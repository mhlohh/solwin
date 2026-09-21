import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger
from app.models.analysis import Analysis
from app.models.conversation import Conversation
from app.models.enums import ConversationChannel, ConversationStatus, SenderType
from app.models.message import Message
from app.models.threat import Threat
from app.schemas.analysis import CustomerIntelligenceOutput
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
)
from app.schemas.message import MessageCreate
from app.services.security.risk_engine import SecurityAnalysisResult

logger = get_logger("solwin.conversation_service")


class ConversationService:
    @staticmethod
    def generate_reference(db: Session) -> str:
        """Generate a unique human-readable reference, e.g. CONV-000001."""
        count = db.scalar(select(func.count(Conversation.id))) or 0
        ref_num = count + 1
        while True:
            candidate = f"CONV-{ref_num:06d}"
            existing = db.scalar(
                select(Conversation.id).where(
                    Conversation.conversation_reference == candidate
                )
            )
            if not existing:
                return candidate
            ref_num += 1

    @staticmethod
    def create_conversation(
        db: Session,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a conversation with an optional initial message transactionally."""
        try:
            with db.begin_nested():
                ref = ConversationService.generate_reference(db)
                now = datetime.now(timezone.utc)
                conversation = Conversation(
                    id=uuid.uuid4(),
                    conversation_reference=ref,
                    customer_name=data.customer_name,
                    customer_email=data.customer_email,
                    channel=data.channel,
                    subject=data.subject,
                    status=ConversationStatus.OPEN,
                    created_at=now,
                    updated_at=now,
                )
                db.add(conversation)
                db.flush()

                if data.initial_message and data.initial_message.strip():
                    message = Message(
                        id=uuid.uuid4(),
                        conversation_id=conversation.id,
                        sender_type=SenderType.CUSTOMER,
                        sender_name=data.customer_name or "Customer",
                        content=data.initial_message.strip(),
                        created_at=now,
                    )
                    db.add(message)
                    db.flush()

            db.commit()
            db.refresh(conversation)
            return conversation
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to create conversation: {exc}", exc_info=False)
            raise

    @staticmethod
    def list_conversations(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ConversationStatus] = None,
        channel: Optional[ConversationChannel] = None,
        assigned_agent_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Conversation], int, int]:
        """Return a paginated list of conversations matching filters."""
        query = select(Conversation)

        if status:
            query = query.where(Conversation.status == status)
        if channel:
            query = query.where(Conversation.channel == channel)
        if assigned_agent_id:
            query = query.where(Conversation.assigned_agent_id == assigned_agent_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Conversation.conversation_reference.ilike(term),
                    Conversation.customer_name.ilike(term),
                    Conversation.customer_email.ilike(term),
                    Conversation.subject.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_stmt) or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        # Deterministic ordering & pagination
        offset = (page - 1) * page_size
        items_stmt = (
            query.order_by(Conversation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(db.scalars(items_stmt).all())

        return items, total, total_pages

    @staticmethod
    def get_conversation_detail(
        db: Session,
        conversation_id: uuid.UUID,
    ) -> Optional[Conversation]:
        """Retrieve conversation with messages, agent, analysis and threats."""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.assigned_agent),
                selectinload(Conversation.messages),
                selectinload(Conversation.analysis_records),
                selectinload(Conversation.threat_records),
            )
        )
        return db.scalar(stmt)

    @staticmethod
    def update_conversation(
        db: Session,
        conversation_id: uuid.UUID,
        data: ConversationUpdate,
    ) -> Optional[Conversation]:
        """Update conversation fields."""
        conversation = db.scalar(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if not conversation:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(conversation, field, value)

        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def delete_conversation(
        db: Session,
        conversation_id: uuid.UUID,
    ) -> bool:
        """Delete conversation by ID, triggering cascade for child records."""
        conversation = db.scalar(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if not conversation:
            return False

        db.delete(conversation)
        db.commit()
        return True

    @staticmethod
    def create_message(
        db: Session,
        conversation_id: uuid.UUID,
        data: MessageCreate,
    ) -> Optional[Message]:
        """Create a new message for a verified conversation."""
        conversation_exists = db.scalar(
            select(Conversation.id).where(Conversation.id == conversation_id)
        )
        if not conversation_exists:
            return None

        now = datetime.now(timezone.utc)
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            sender_type=data.sender_type,
            sender_name=data.sender_name,
            content=data.content.strip(),
            created_at=now,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def list_messages(
        db: Session,
        conversation_id: uuid.UUID,
    ) -> Optional[List[Message]]:
        """List messages in deterministic order for an existing conversation."""
        conversation_exists = db.scalar(
            select(Conversation.id).where(Conversation.id == conversation_id)
        )
        if not conversation_exists:
            return None

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_latest_analysis(
        db: Session,
        conversation_id: uuid.UUID,
    ) -> Optional[Analysis]:
        """Retrieve the most recent analysis record for a conversation."""
        stmt = (
            select(Analysis)
            .where(Analysis.conversation_id == conversation_id)
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        return db.scalar(stmt)

    @staticmethod
    def save_or_update_analysis(
        db: Session,
        conversation_id: uuid.UUID,
        intelligence: CustomerIntelligenceOutput,
    ) -> Analysis:
        """Save or update analysis avoiding uncontrolled duplicate records."""
        existing = ConversationService.get_latest_analysis(db, conversation_id)
        now = datetime.now(timezone.utc)

        if existing:
            existing.category = intelligence.category.value
            existing.issue = intelligence.issue
            existing.sentiment = intelligence.sentiment.value
            existing.emotion = intelligence.emotion
            existing.priority = intelligence.priority.value
            existing.resolution_status = intelligence.resolution_status.value
            existing.summary = intelligence.summary
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        analysis = Analysis(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            category=intelligence.category.value,
            issue=intelligence.issue,
            sentiment=intelligence.sentiment.value,
            emotion=intelligence.emotion,
            priority=intelligence.priority.value,
            resolution_status=intelligence.resolution_status.value,
            summary=intelligence.summary,
            created_at=now,
            updated_at=now,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    @staticmethod
    def get_latest_threat(
        db: Session,
        conversation_id: uuid.UUID,
    ) -> Optional[Threat]:
        """Retrieve the most recent threat analysis record for a conversation."""
        stmt = (
            select(Threat)
            .where(Threat.conversation_id == conversation_id)
            .order_by(Threat.created_at.desc())
            .limit(1)
        )
        return db.scalar(stmt)

    @staticmethod
    def save_or_update_threat(
        db: Session,
        conversation_id: uuid.UUID,
        security_result: SecurityAnalysisResult,
    ) -> Threat:
        """Save or update threat analysis avoiding uncontrolled duplicates."""
        existing = ConversationService.get_latest_threat(db, conversation_id)
        now = datetime.now(timezone.utc)

        if existing:
            existing.threat_detected = security_result.threat_detected
            existing.threat_type = security_result.threat_type
            existing.social_engineering_detected = (
                security_result.social_engineering_detected
            )
            existing.techniques = security_result.techniques
            existing.risk_level = security_result.risk_level
            existing.suspicious_urls = security_result.suspicious_urls
            existing.suspicious_emails = security_result.suspicious_emails
            existing.risk_reasons = security_result.risk_reasons
            existing.recommended_action = security_result.recommended_action
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        threat = Threat(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            threat_detected=security_result.threat_detected,
            threat_type=security_result.threat_type,
            social_engineering_detected=security_result.social_engineering_detected,
            techniques=security_result.techniques,
            risk_level=security_result.risk_level,
            suspicious_urls=security_result.suspicious_urls,
            suspicious_emails=security_result.suspicious_emails,
            risk_reasons=security_result.risk_reasons,
            recommended_action=security_result.recommended_action,
            created_at=now,
            updated_at=now,
        )
        db.add(threat)
        db.commit()
        db.refresh(threat)
        return threat
