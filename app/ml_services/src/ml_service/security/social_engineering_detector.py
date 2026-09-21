"""Local rule-based social-engineering detector — the PRIMARY SE tier.

Deterministic, zero-cost, millisecond-fast cascade over operational signals.
Gemini remains as a secondary cross-check one tier up; this module is what
production serves when the local path is authoritative.

Rules (first match wins → techniques):
* URGENCY            — time pressure to bypass rational checks
* THREAT_COERCION    — negative-consequence threats
* CREDENTIAL_HARVESTING — asks for passwords/OTPs/secrets
* OTP_REQUEST        — explicit one-time-code requests
* PASSWORD_REQUEST   — explicit password requests
* IMPERSONATION      — claiming to be staff/security/bank
* PAYMENT_MANIPULATION — pressure to move money off-platform
"""

import re

from ml_service.api.schemas import SocialEngineeringResult, SocialEngineeringTechnique

_RULES: list[tuple[str, str, str]] = [
    # (rule_id, technique, pattern)
    ("SE-CRED", "CREDENTIAL_HARVESTING",
     r"\b(?:your\s+)?(?:password|passcode|pin)\s+(?:is|:|enter|provide|share|send|confirm)\b"
     r"|\b(?:enter|provide|share|send|confirm)\s+(?:your\s+)?(?:password|passcode|pin)\b"
     r"|\b(?:my\s+)?password\s+is\b"),
    ("SE-OTP", "OTP_REQUEST",
     r"\b(?:otp|one[-\s]?time\s+(?:code|password)|verification\s+code)\b"
     r".{0,40}\b(?:share|send|provide|confirm|enter|read\s+out|tell)\b"
     r"|\b(?:share|send|provide|confirm|enter|read\s+out|tell)\b.{0,40}\b(?:otp|one[-\s]?time\s+(?:code|password)|verification\s+code)\b"),
    ("SE-PWD", "PASSWORD_REQUEST",
     r"\b(?:share|send|tell|reveal|give)\s+(?:me\s+)?(?:your|the)\s+password\b"),
    ("SE-THREAT", "THREAT_COERCION",
     r"\b(?:account\s+will\s+be\s+(?:permanently\s+)?(?:closed|suspended|terminated|deleted)\b"
     r"|legal\s+action\s+will\s+be\s+taken\b"
 r"|warrant\s+for\s+your\s+arrest\b"
     r"|\b(?:immediate\s+)?(?:suspension|closure|deactivation)\s+(?:notice|warning)\b)"),
    ("SE-THREAT2", "THREAT_COERCION",
     r"\b(?:act\s+now\s+or|last\s+(warning|chance)|final\s+warning)\b"),
    ("SE-URG", "URGENCY",
     r"\b(?:within\s+\d+\s+(?:hours|minutes|days)|\d+\s+hours?\b.{0,20}\b(?:or|before)\b"
     r"|act\s+now\b|immediate(?:ly)?\s+(?:action|response|verification|required|confirm)\b"
     r"|urgent(?:ly)?\s+(?:action|verify|confirm|respond)\b"
     r"|expires?\s+(?:today|tomorrow|in\s+\d+)\b|\bdeadlines?\b.{0,20}\b(?:today|tomorrow|now)\b)"),
    ("SE-URG2", "URGENCY",
     r"\b(?:verify|confirm|validate|update)\s+(?:your\s+)?(?:account|identity|details|information|password|payment)\b.{0,60}\b(?:now|immediately|within|today|right\s+away)\b"),
    ("SE-IMPERSON", "IMPERSONATION",
     r"\b(?:I\s+am|this\s+is)\s+(?:the\s+)?(?:security|support|tech(?:nical)?|account)\s+(?:team|agent|manager|department)\b"
     r"|\b(?:from\s+the\s+)?(?:security|support)\s+department\b"
     r"|\bcalling\s+from\s+\w+\s+(?:bank|company)\b"
     r"|\bIT\s+(?:admin|administrator|support|department)\b"),
    ("SE-PAY", "PAYMENT_MANIPULATION",
     r"\b(?:gift\s+cards?|wire\s+transfer|crypto(?:currency)?|bitcoin)\b.{0,40}\b(?:pay|send|purchase|buy)\b"
     r"|\b(?:pay|send|purchase|buy)\b.{0,40}\b(?:gift\s+cards?|wire\s+transfer|crypto(?:currency)?|bitcoin)\b"
     r"|\bprocessing\s+fee\s+(?:to\s+release|before)\b"),
]


class SocialEngineeringDetector:
    """Rule-based social-engineering detection (primary tier)."""

    def __init__(self) -> None:
        self._compiled = [
            (rule_id, technique, re.compile(pattern, re.IGNORECASE))
            for rule_id, technique, pattern in _RULES
        ]

    def detect(
        self,
        message: str | None,
        subject: str | None = None,
    ) -> SocialEngineeringResult:
        text = f"{subject or ''}\n{message or ''}".strip()
        if not text:
            return SocialEngineeringResult(
                detected=False,
                techniques=[],
                reason="No content provided.",
                provider="local",
            )

        techniques: list[SocialEngineeringTechnique] = []
        evidence: list[str] = []
        for rule_id, technique, pattern in self._compiled:
            m = pattern.search(text)
            if m:
                try:
                    t = SocialEngineeringTechnique(technique)
                except ValueError:
                    continue
                if t not in techniques:
                    techniques.append(t)
                evidence.append(f"{rule_id}:{m.group(0).strip()[:60]}")

        if techniques:
            return SocialEngineeringResult(
                detected=True,
                techniques=techniques,
                reason=f"Rule matches: {'; '.join(evidence[:3])}",
                provider="local",
            )

        return SocialEngineeringResult(
            detected=False,
            techniques=[],
            reason="No social-engineering rule matched.",
            provider="local",
        )
