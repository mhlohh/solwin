import re

from ml_service.api.schemas import ResolutionResult, ResolutionStatus
from ml_service.preprocessing.cleaner import build_complaint_text

RESOLVED_PATTERNS = [
    (r"\b(issue|problem|ticket)\s+(is\s+)?resolved\b", "issue_resolved_acknowledgment"),
    (
        r"\breceived\s+(my\s+)?(refund|money|parcel|package|order|delivery)\b",
        "received_delivery_or_refund",
    ),
    (r"\bfixed\s+now\b|\bworking\s+now\b", "system_working_now"),
    (
        r"\bthank\s+you\s+for\s+(the\s+)?help\b|\bthanks\s+problem\s+solved\b",
        "gratitude_for_resolution",
    ),
]

UNRESOLVED_PATTERNS = [
    (
        r"\b(still|yet)\s+(not|haven't|havent)\s+(received|got|resolved)\b",
        "still_unresolved_complaint",
    ),
    (
        r"\bwaiting\s+for\s+(response|reply|refund|update|delivery|courier)\b",
        "waiting_for_response_or_refund",
    ),
    (r"\bno\s+(update|response|reply|action)\s+yet\b", "no_support_response_yet"),
    (
        r"\bwhen\s+will\s+(i\s+get|this\s+be\s+resolved|my\s+parcel\s+arrive)\b",
        "repeated_status_inquiry",
    ),
    (r"\bhas\s+not\s+arrived\b|\bhasn't\s+arrived\b", "missing_order"),
]

PARTIAL_PATTERNS = [
    (r"\bpartial\s+refund\b", "partial_refund_issued"),
    (r"\breplacement\s+dispatched\b|\bexchange\s+in\s+progress\b", "exchange_in_progress"),
    (r"\bone\s+item\s+arrived\b|\bpartially\s+delivered\b", "partial_delivery_received"),
]


class ResolutionDetector:
    """Detects resolution state without using sentiment or anger as a proxy for resolution."""

    def __init__(self) -> None:
        self.resolved_compiled = [
            (re.compile(p, re.IGNORECASE), name) for p, name in RESOLVED_PATTERNS
        ]
        self.unresolved_compiled = [
            (re.compile(p, re.IGNORECASE), name) for p, name in UNRESOLVED_PATTERNS
        ]
        self.partial_compiled = [
            (re.compile(p, re.IGNORECASE), name) for p, name in PARTIAL_PATTERNS
        ]

    def detect(
        self,
        message: str | None,
        subject: str | None = None,
    ) -> ResolutionResult:
        text = build_complaint_text(message, subject)
        if not text:
            return ResolutionResult(
                status=ResolutionStatus.UNKNOWN,
                confidence=1.0,
                signals=["empty_message"],
                pending_items=[],
            )

        # Check Partial
        partial_signals: list[str] = []
        for pattern, sig_name in self.partial_compiled:
            if pattern.search(text):
                partial_signals.append(sig_name)

        if partial_signals:
            return ResolutionResult(
                status=ResolutionStatus.PARTIALLY_RESOLVED,
                confidence=0.85,
                signals=partial_signals,
                pending_items=["Final resolution confirmation required"],
            )

        # Check Resolved
        resolved_signals: list[str] = []
        for pattern, sig_name in self.resolved_compiled:
            if pattern.search(text):
                resolved_signals.append(sig_name)

        # Check Unresolved
        unresolved_signals: list[str] = []
        for pattern, sig_name in self.unresolved_compiled:
            if pattern.search(text):
                unresolved_signals.append(sig_name)

        # If explicit resolution acknowledgment exists and no ongoing complaint indicators
        if resolved_signals and not unresolved_signals:
            return ResolutionResult(
                status=ResolutionStatus.RESOLVED,
                confidence=0.90,
                signals=resolved_signals,
                pending_items=[],
            )

        if unresolved_signals:
            return ResolutionResult(
                status=ResolutionStatus.UNRESOLVED,
                confidence=0.85,
                signals=unresolved_signals,
                pending_items=["Awaiting merchant or courier response"],
            )

        return ResolutionResult(
            status=ResolutionStatus.UNKNOWN,
            confidence=0.60,
            signals=["no_explicit_resolution_indicators"],
            pending_items=[],
        )
