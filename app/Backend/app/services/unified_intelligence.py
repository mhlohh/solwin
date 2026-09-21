import asyncio
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.analysis import Analysis
from app.models.enums import (
    ComplaintCategory,
    Priority,
    ResolutionStatus,
    RiskLevel,
    SenderType,
    Sentiment,
)
from app.models.message import Message
from app.models.threat import Threat
from app.schemas.analysis import CustomerIntelligenceOutput
from app.schemas.unified import (
    CustomerIntelligenceSummary,
    SecurityIntelligenceSummary,
    UnifiedAnalysisResponse,
)
from app.services.ai.customer_intelligence import (
    CustomerIntelligenceError,
    CustomerIntelligenceService,
)
from app.services.conversation_service import ConversationService
from app.services.security.risk_engine import (
    RiskEngine,
    SecurityAnalysisResult,
)

logger = get_logger("solwin.unified_intelligence")


class UnifiedIntelligenceError(Exception):
    """Exception raised for errors during unified intelligence execution."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnifiedIntelligenceService:
    @staticmethod
    def determine_final_action(
        customer_intel: CustomerIntelligenceSummary,
        security_intel: SecurityIntelligenceSummary,
    ) -> str:
        """Deterministically determine the final recommended action.

        Calibrates between customer urgency and security threat levels without
        overwriting customer priority or ignoring security risks.
        """
        risk = security_intel.risk_level.upper()
        cust_priority = customer_intel.priority

        # 1. Critical Security Threat
        if risk == RiskLevel.CRITICAL.value:
            return (
                "Escalate immediately to the security team. Do not click links, "
                "execute requested commands, or request/provide credentials or OTPs."
            )

        # 2. High Security Threat
        if risk == RiskLevel.HIGH.value:
            if cust_priority in [Priority.HIGH, Priority.CRITICAL]:
                return (
                    "High priority customer inquiry flagged with significant "
                    "security risk. Escalate to security before fulfilling "
                    "customer request."
                )
            return (
                "Escalate for security review. Verify sender authenticity "
                "before taking action."
            )

        # 3. Medium Security Threat
        if risk == RiskLevel.MEDIUM.value:
            if cust_priority == Priority.CRITICAL:
                return (
                    "Critical customer urgency with potential security anomalies. "
                    "Handle urgent customer issue with verified identity safeguards."
                )
            return (
                "Review the message for suspicious indicators and verify "
                "sender identity before taking action."
            )

        # 4. Low Security Risk (No active threat) - Calibrated by Customer Priority
        if cust_priority == Priority.CRITICAL:
            return (
                "Critical customer urgency with no security threats detected. "
                "Immediately route to senior support or engineering team."
            )
        if cust_priority == Priority.HIGH:
            return (
                "High priority customer issue with no security threat. "
                "Expedite support response and resolution."
            )
        if cust_priority == Priority.MEDIUM:
            return (
                "Standard support priority. Proceed with standard triage "
                "and queue resolution."
            )

        return "Continue normal support handling."

    @staticmethod
    def analyze_direct_message(
        message_text: str,
        expected_domain: Optional[str] = None,
    ) -> UnifiedAnalysisResponse:
        """Run direct synchronous analysis on a single text payload without DB write."""
        if not message_text or not message_text.strip():
            raise UnifiedIntelligenceError(
                "Cannot analyze empty message content.", status_code=400
            )

        # 1. Run Customer Intelligence
        pseudo_msg = Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            sender_type=SenderType.CUSTOMER,
            content=message_text.strip(),
        )
        ai_service = CustomerIntelligenceService()
        try:
            cust_output: CustomerIntelligenceOutput = ai_service.analyze_conversation(
                [pseudo_msg]
            )
        except CustomerIntelligenceError as exc:
            raise UnifiedIntelligenceError(
                exc.message, status_code=exc.status_code
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected customer intelligence error: {exc}")
            raise UnifiedIntelligenceError(
                "Customer intelligence analysis failed.", status_code=500
            ) from exc

        # 2. Run Security Intelligence
        risk_engine = RiskEngine()
        try:
            sec_output: SecurityAnalysisResult = risk_engine.evaluate(
                text=message_text.strip(),
                expected_domain=expected_domain,
            )
        except Exception as exc:
            logger.error(f"Unexpected security intelligence error: {exc}")
            raise UnifiedIntelligenceError(
                "Security intelligence analysis failed.", status_code=500
            ) from exc

        cust_summary = CustomerIntelligenceSummary(
            category=cust_output.category,
            issue=cust_output.issue,
            sentiment=cust_output.sentiment,
            emotion=cust_output.emotion,
            priority=cust_output.priority,
            resolution_status=cust_output.resolution_status,
            summary=cust_output.summary,
        )

        sec_summary = SecurityIntelligenceSummary(
            threat_detected=sec_output.threat_detected,
            threat_type=sec_output.threat_type,
            suspicious_urls=sec_output.suspicious_urls,
            suspicious_emails=sec_output.suspicious_emails,
            social_engineering_detected=sec_output.social_engineering_detected,
            techniques=sec_output.techniques,
            risk_level=sec_output.risk_level,
            risk_reasons=sec_output.risk_reasons,
        )

        final_action = UnifiedIntelligenceService.determine_final_action(
            cust_summary, sec_summary
        )

        return UnifiedAnalysisResponse(
            conversation_id=None,
            customer_intelligence=cust_summary,
            security_intelligence=sec_summary,
            recommended_action=final_action,
        )

    @staticmethod
    def analyze_conversation(
        db: Session,
        conversation_id: uuid.UUID,
    ) -> UnifiedAnalysisResponse:
        """Run customer and security intelligence for a conversation and persist."""
        # 1. Load conversation detail
        conversation = ConversationService.get_conversation_detail(db, conversation_id)
        if not conversation:
            raise UnifiedIntelligenceError(
                f"Conversation with ID '{conversation_id}' not found.",
                status_code=404,
            )

        messages = conversation.messages
        if not messages:
            raise UnifiedIntelligenceError(
                "Cannot analyze an empty conversation with no messages.",
                status_code=400,
            )

        # 2. Run Customer Intelligence
        ai_service = CustomerIntelligenceService()

        try:
            cust_output: CustomerIntelligenceOutput = ai_service.analyze_conversation(
                messages=messages,
                subject=conversation.subject,
            )
        except CustomerIntelligenceError as exc:
            raise UnifiedIntelligenceError(
                exc.message, status_code=exc.status_code
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected customer intelligence error: {exc}")
            raise UnifiedIntelligenceError(
                "Customer intelligence analysis failed.", status_code=500
            ) from exc

        # 3. Aggregate text and Run Security Intelligence
        combined_texts = []
        if conversation.subject:
            combined_texts.append(f"Subject: {conversation.subject}")
        for msg in messages:
            sender = (
                msg.sender_type.value
                if hasattr(msg.sender_type, "value")
                else str(msg.sender_type)
            )
            sender_label = f"[{sender}]"
            if msg.sender_name:
                sender_label += f" {msg.sender_name}"
            combined_texts.append(f"{sender_label}: {msg.content}")

        aggregated_text = "\n".join(combined_texts)
        risk_engine = RiskEngine()
        try:
            sec_output: SecurityAnalysisResult = risk_engine.evaluate(
                text=aggregated_text
            )
        except Exception as exc:
            logger.error(f"Unexpected security intelligence error: {exc}")
            raise UnifiedIntelligenceError(
                "Security intelligence analysis failed.", status_code=500
            ) from exc

        # 4. Determine final recommended action
        cust_summary = CustomerIntelligenceSummary(
            category=cust_output.category,
            issue=cust_output.issue,
            sentiment=cust_output.sentiment,
            emotion=cust_output.emotion,
            priority=cust_output.priority,
            resolution_status=cust_output.resolution_status,
            summary=cust_output.summary,
        )

        sec_summary = SecurityIntelligenceSummary(
            threat_detected=sec_output.threat_detected,
            threat_type=sec_output.threat_type,
            suspicious_urls=sec_output.suspicious_urls,
            suspicious_emails=sec_output.suspicious_emails,
            social_engineering_detected=sec_output.social_engineering_detected,
            techniques=sec_output.techniques,
            risk_level=sec_output.risk_level,
            risk_reasons=sec_output.risk_reasons,
        )

        final_action = UnifiedIntelligenceService.determine_final_action(
            cust_summary, sec_summary
        )

        # 5. Persist Analysis and Threat records idempotently
        # Update recommended_action on analysis / threat objects
        analysis_record = ConversationService.save_or_update_analysis(
            db=db,
            conversation_id=conversation_id,
            intelligence=cust_output,
        )
        analysis_record.recommended_action = final_action

        sec_output.recommended_action = final_action
        threat_record = ConversationService.save_or_update_threat(
            db=db,
            conversation_id=conversation_id,
            security_result=sec_output,
        )
        db.commit()

        return UnifiedAnalysisResponse(
            conversation_id=conversation_id,
            customer_intelligence=cust_summary,
            security_intelligence=sec_summary,
            recommended_action=final_action,
        )

    @staticmethod
    def get_latest_unified_analysis(
        db: Session,
        conversation_id: uuid.UUID,
    ) -> UnifiedAnalysisResponse:
        """Fetch latest persisted analysis without triggering AI or security re-run."""
        conversation = ConversationService.get_conversation_detail(db, conversation_id)
        if not conversation:
            raise UnifiedIntelligenceError(
                f"Conversation with ID '{conversation_id}' not found.",
                status_code=404,
            )

        analysis: Optional[Analysis] = ConversationService.get_latest_analysis(
            db, conversation_id
        )
        threat: Optional[Threat] = ConversationService.get_latest_threat(
            db, conversation_id
        )

        if not analysis and not threat:
            raise UnifiedIntelligenceError(
                f"No analysis found for conversation '{conversation_id}'.",
                status_code=404,
            )

        # Build summaries from stored records
        cust_summary = CustomerIntelligenceSummary(
            category=(
                ComplaintCategory(analysis.category)
                if analysis and analysis.category
                else ComplaintCategory.OTHER
            ),
            issue=(
                analysis.issue if analysis and analysis.issue else "No issue recorded"
            ),
            sentiment=(
                Sentiment(analysis.sentiment)
                if analysis and analysis.sentiment
                else Sentiment.NEUTRAL
            ),
            emotion=analysis.emotion if analysis and analysis.emotion else "Neutral",
            priority=(
                Priority(analysis.priority)
                if analysis and analysis.priority
                else Priority.LOW
            ),
            resolution_status=(
                ResolutionStatus(analysis.resolution_status)
                if analysis and analysis.resolution_status
                else ResolutionStatus.UNRESOLVED
            ),
            summary=analysis.summary if analysis and analysis.summary else "",
        )

        sec_summary = SecurityIntelligenceSummary(
            threat_detected=bool(threat and threat.threat_detected),
            threat_type=threat.threat_type if threat and threat.threat_type else "NONE",
            suspicious_urls=(
                threat.suspicious_urls if threat and threat.suspicious_urls else []
            ),
            suspicious_emails=(
                threat.suspicious_emails if threat and threat.suspicious_emails else []
            ),
            social_engineering_detected=bool(
                threat and threat.social_engineering_detected
            ),
            techniques=threat.techniques if threat and threat.techniques else [],
            risk_level=(
                threat.risk_level
                if threat and threat.risk_level
                else RiskLevel.LOW.value
            ),
            risk_reasons=threat.risk_reasons if threat and threat.risk_reasons else [],
        )

        rec_action = (
            (
                analysis.recommended_action
                if analysis and analysis.recommended_action
                else None
            )
            or (
                threat.recommended_action
                if threat and threat.recommended_action
                else None
            )
            or UnifiedIntelligenceService.determine_final_action(
                cust_summary, sec_summary
            )
        )

        return UnifiedAnalysisResponse(
            conversation_id=conversation_id,
            customer_intelligence=cust_summary,
            security_intelligence=sec_summary,
            recommended_action=rec_action,
        )
