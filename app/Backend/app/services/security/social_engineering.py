import re
from typing import Dict, List

from pydantic import BaseModel, Field

# Centralized rules and explainable indicators for social engineering
TECHNIQUE_PATTERNS: Dict[str, List[re.Pattern]] = {
    "URGENCY": [
        re.compile(
            r"\b(urgent|urgently|immediate|immediately|right now|within \d+ "
            r"(?:hours?|minutes?)|account will be "
            r"(?:suspended|terminated|closed|deleted|blocked)|"
            r"final notice|action required)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(asap|do not delay|critical alert|warning: unauthorized|"
            r"threat detected|suspend your access)\b",
            re.IGNORECASE,
        ),
    ],
    "CREDENTIAL_HARVESTING": [
        re.compile(
            r"\b(enter (?:your )?(?:password|credentials|login|passcode|"
            r"secret key|pin)|provide (?:your )?(?:password|credentials)|"
            r"verify (?:your )?password|reset (?:your )?password here|"
            r"update (?:your )?login)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(confirm (?:your )?identity by entering|"
            r"click (?:the link|here) to (?:sign in|log in|verify "
            r"(?:your )?account))\b",
            re.IGNORECASE,
        ),
    ],
    "OTP_REQUEST": [
        re.compile(
            r"\b(otp|one[- ]time[- ]password|verification code|"
            r"security code|2fa code|mfa code|sms code|auth code|"
            r"6[- ]digit code)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(send (?:us|me) the (?:code|otp)|share (?:your )?otp|"
            r"forward the (?:verification )?code)\b",
            re.IGNORECASE,
        ),
    ],
    "IMPERSONATION": [
        re.compile(
            r"\b(?:from )?(?:microsoft|paypal|google|apple|amazon|netflix|"
            r"bank of america|chase|wells fargo|solwin)\s+"
            r"(?:security|support|team|helpdesk)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(official (?:support|security|helpdesk|admin|administrator|"
            r"it department|fraud prevention)(?: team)?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(i am (?:from|calling from|contacting you from) "
            r"(?:it|security|support|the bank))\b",
            re.IGNORECASE,
        ),
    ],
}


class SocialEngineeringResult(BaseModel):
    detected: bool = False
    techniques: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)


class SocialEngineeringDetector:
    def detect(self, text: str) -> SocialEngineeringResult:
        """Analyze text for social engineering techniques explainably."""
        if not text:
            return SocialEngineeringResult(detected=False, techniques=[], signals=[])

        detected_techniques = []
        signals = []

        for technique, patterns in TECHNIQUE_PATTERNS.items():
            matched = False
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    matched = True
                    # Clean match string
                    if isinstance(matches[0], str):
                        first_match = matches[0]
                    else:
                        first_match = matches[0][0]
                    signals.append(
                        f"{technique}: triggered by lure '{first_match.strip()}'"
                    )
                    break

            if matched:
                detected_techniques.append(technique)

        return SocialEngineeringResult(
            detected=len(detected_techniques) > 0,
            techniques=detected_techniques,
            signals=signals,
        )
