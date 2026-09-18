"""Deterministic priority assignment for raw customer feedback.

Priority is derived from the dataset's own signals (phishing flag, technique,
intent, issue, label) so the ranking is reproducible and auditable — no ML in
the serving path. Tiers: CRITICAL > HIGH > MEDIUM > LOW.

The inbox queue is priority-first and FIFO within a tier (oldest first), so
listing order is (priority_rank ASC, created_at ASC, id ASC).
"""
from typing import Optional

# Lower rank == more important. Sort ascending to put the queue in priority order.
PRIORITY_RANKS = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}

# ---------------------------------------------------------------- technique
_TECHNIQUE_RULES = [
    ("CRITICAL", ("credential harvesting", "otp request", "malware delivery")),
    ("HIGH", ("urgency", "impersonation", "account verification", "fake invoice")),
]

# ------------------------------------------------------------------- intent
_INTENT_RULES = [
    ("CRITICAL", ("credential harvesting", "malware")),
    ("HIGH", (
        "fraudulent user", "financial scam", "security notification",
        "fake invoice", "malware attachment", "unable to login",
    )),
    ("MEDIUM", (
        "payment related queries", "payment pending", "online payment issues",
        "refund enquiry", "refund related issues", "card/emi", "paylater related",
        "wallet related", "commission related", "life insurance",
    )),
]

# -------------------------------------------------------------------- issue
_ISSUE_RULES = [
    ("CRITICAL", ("credential harvesting", "account compromise", "otp")),
    ("HIGH", (
        "phishing", "fraud", "scam", "hacked", "unauthorized", "compromis",
        "stolen", "suspicious",
    )),
    ("MEDIUM", (
        "payment", "refund", "charge", "billing", "transaction",
        "urgent", "escalat", "immediately", "asap", "complaint",
    )),
]

# -------------------------------------------------------------------- label
_LABEL_RULES = [
    ("CRITICAL", ("credential harvesting", "phishing")),
    ("HIGH", ("smishing", "vishing", "scam", "fraud", "spam")),
]


def _match(text: Optional[str], rules) -> Optional[str]:
    """Return the highest tier whose keyword appears in text (case-insensitive)."""
    if not isinstance(text, str) or not text:
        return None
    lowered = text.lower()
    for tier, keywords in rules:
        if any(k in lowered for k in keywords):
            return tier
    return None


def assign_priority(
    phishing: Optional[bool],
    technique: Optional[str] = None,
    intent: Optional[str] = None,
    issue: Optional[str] = None,
    label: Optional[str] = None,
) -> str:
    """Derive the priority tier from dataset signals.

    Deterministic precedence: phishing flag > technique > intent > issue > label.
    First match wins; default is LOW.
    """
    if phishing:
        return "CRITICAL"
    for text, rules in (
        (technique, _TECHNIQUE_RULES),
        (intent, _INTENT_RULES),
        (issue, _ISSUE_RULES),
        (label, _LABEL_RULES),
    ):
        tier = _match(text, rules)
        if tier:
            return tier
    return "LOW"
