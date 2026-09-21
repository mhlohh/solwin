import logging
import re
from typing import Any

from ml_service.api.schemas import ConversationSummary, ResolutionStatus
from ml_service.preprocessing.cleaner import build_complaint_text, normalize_text
from ml_service.resolution.detector import ResolutionDetector

logger = logging.getLogger(__name__)

ORDER_ID_PATTERN = re.compile(
    r"\b(?:order|tracking|ticket|invoice|txn|ref)[\s#:]*([A-Za-z0-9\-_]{5,20})\b|"
    r"#([A-Za-z0-9\-_]{4,15})\b",
    re.IGNORECASE,
)
AMOUNT_PATTERN = re.compile(
    r"(?:[\$€£₹]|USD|EUR|GBP|INR)\s*[\d,]+(?:\.\d{1,2})?|"
    r"\b\d+(?:[,\.]\d{2})?\s*(?:dollars|euros|pounds|rupees|cents)\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4})\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

ACTION_TAKEN_PATTERNS = [
    (r"\b(already\s+contacted|already\s+emailed|already\s+called)\b", "Contacted support team"),
    (r"\b(returned\s+the\s+item|sent\s+back|returned\s+package)\b", "Customer returned item"),
    (
        r"\b(tried\s+restarting|reset\s+password|cleared\s+cache)\b",
        "Customer attempted troubleshooting",
    ),
    (
        r"\b(reported\s+to\s+bank|disputed\s+charge|cancelled\s+card)\b",
        "Reported to financial institution",
    ),
    (r"\b(paid\s+via|transferred\s+money|sent\s+payment)\b", "Payment completed by customer"),
    (r"\b(refund\s+requested|asked\s+for\s+refund)\b", "Refund formally requested"),
]

PENDING_ACTION_PATTERNS = [
    (
        r"\b(waiting\s+for|awaiting)\s+(response|reply|update|refund|delivery)\b",
        "Awaiting status update/response",
    ),
    (
        r"\b(need|want|demand)\s+(a\s+)?(refund|replacement|explanation)\b",
        "Pending refund or replacement resolution",
    ),
    (
        r"\b(please\s+(investigate|resolve|fix|help|check|update))\b",
        "Investigation/resolution required",
    ),
    (
        r"\b(unblock|reset|restore)\s+(my\s+)?account\b",
        "Account access restoration required",
    ),
    (
        r"\b(where\s+is\s+my|when\s+will\s+i\s+receive)\b",
        "Order delivery status inquiry to address",
    ),
]


class ConversationSummarizer:
    """Extracts structured summaries and key entities from customer conversations."""

    def __init__(self, resolution_detector: ResolutionDetector | None = None) -> None:
        self.resolution_detector = resolution_detector or ResolutionDetector()

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        entities: dict[str, list[str]] = {}

        # Order IDs
        order_matches = ORDER_ID_PATTERN.findall(text)
        flat_orders = [m[0] or m[1] for m in order_matches if (m[0] or m[1])]
        if flat_orders:
            entities["order_ids"] = list(dict.fromkeys(flat_orders))

        # Amounts
        amounts = AMOUNT_PATTERN.findall(text)
        if amounts:
            entities["monetary_amounts"] = list(dict.fromkeys(amounts))

        # Dates
        dates = DATE_PATTERN.findall(text)
        if dates:
            entities["dates"] = list(dict.fromkeys(dates))

        # Emails
        emails = EMAIL_PATTERN.findall(text)
        if emails:
            entities["emails"] = list(dict.fromkeys(emails))

        # Phone numbers
        phones = PHONE_PATTERN.findall(text)
        if phones:
            entities["phone_numbers"] = list(dict.fromkeys(phones))

        return entities

    def summarize(
        self,
        message: str | None,
        subject: str | None = None,
        prefer_llm: bool = False,
        gemini_output: object | None = None,
    ) -> ConversationSummary:
        combined = build_complaint_text(message, subject)
        cleaned_combined = normalize_text(combined)

        if not cleaned_combined:
            return ConversationSummary(
                customer_issue="No message content provided.",
                actions_taken=[],
                pending_actions=[],
                resolution_status=ResolutionStatus.UNKNOWN,
                entities_extracted={},
                summary_mode="extractive",
                key_phrases=[],
            )

        # Resolution detection
        res_result = self.resolution_detector.detect(message, subject)

        # Extract entities
        entities = self.extract_entities(cleaned_combined)

        # Actions taken
        actions_taken: list[str] = []
        for pattern, action_desc in ACTION_TAKEN_PATTERNS:
            if re.search(pattern, cleaned_combined, re.IGNORECASE):
                actions_taken.append(action_desc)

        # Pending actions
        pending_actions: list[str] = []
        for pattern, action_desc in PENDING_ACTION_PATTERNS:
            if re.search(pattern, cleaned_combined, re.IGNORECASE):
                pending_actions.append(action_desc)

        if not pending_actions and res_result.status == ResolutionStatus.UNRESOLVED:
            pending_actions.append("Support team investigation required")

        # Extractive issue formulation
        customer_issue = self._extract_issue_summary(subject, message)
        key_phrases = self._extract_key_phrases(cleaned_combined)

        # LLM path: Gemini output (already computed) or prefer_llm flag
        if prefer_llm or gemini_output is not None:
            llm_summary = self._try_llm_summarize(
                cleaned_combined, customer_issue, gemini_output=gemini_output
            )
            if llm_summary:
                return ConversationSummary(
                    customer_issue=str(llm_summary.get("customer_issue", customer_issue)),
                    actions_taken=list(llm_summary.get("actions_taken", actions_taken)),  # type: ignore[arg-type]
                    pending_actions=list(llm_summary.get("pending_actions", pending_actions)),  # type: ignore[arg-type]
                    resolution_status=res_result.status,
                    entities_extracted=entities,
                    summary_mode="llm",
                    key_phrases=key_phrases,
                )

        return ConversationSummary(
            customer_issue=customer_issue,
            actions_taken=list(dict.fromkeys(actions_taken)),
            pending_actions=list(dict.fromkeys(pending_actions)),
            resolution_status=res_result.status,
            entities_extracted=entities,
            summary_mode="extractive",
            key_phrases=key_phrases,
        )


    def _extract_issue_summary(self, subject: str | None, message: str | None) -> str:
        clean_subj = normalize_text(subject or "")
        clean_msg = normalize_text(message or "")

        sentences = [
            s.strip() for s in re.split(r"[.!?\n]+", clean_msg) if len(s.strip()) > 10
        ]

        lead_sentence = sentences[0] if sentences else clean_msg

        if clean_subj and lead_sentence:
            if clean_subj.lower() in lead_sentence.lower():
                issue = lead_sentence
            else:
                issue = f"{clean_subj}: {lead_sentence}"
        elif clean_subj:
            issue = clean_subj
        elif lead_sentence:
            issue = lead_sentence
        else:
            issue = "Unspecified customer complaint"

        if len(issue) > 280:
            issue = issue[:277] + "..."
        return issue

    def _extract_key_phrases(self, text: str) -> list[str]:
        phrases: list[str] = []
        for match in re.finditer(
            r"\b(?:refund|unauthorized charge|delivery delayed|account locked|"
            r"broken item|missing package|order not received|security breach|password reset)\b",
            text,
            re.IGNORECASE,
        ):
            phrase = match.group(0).lower()
            if phrase not in phrases:
                phrases.append(phrase)
        return phrases

    def _try_llm_summarize(
        self, text: str, fallback_issue: str, gemini_output: object | None = None
    ) -> dict[str, object] | None:
        """Use Gemini summary if already computed by the pipeline, otherwise return None.

        The ``gemini_output`` is a ``GeminiAnalysisOutput`` injected by the route
        handler when Gemini was called.  This avoids a second API call.
        """
        if gemini_output is not None:
            summary_text = getattr(gemini_output, "summary_text", "")
            if summary_text and summary_text.strip():
                logger.info("ConversationSummarizer: using Gemini summary_text")
                return {
                    "customer_issue": summary_text.strip(),
                    "actions_taken": [],
                    "pending_actions": [],
                }

        logger.info("ConversationSummarizer: LLM provider not available, using extractive summary")
        return None

