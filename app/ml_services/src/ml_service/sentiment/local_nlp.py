"""Local NLP sentiment analyzer — the PRIMARY sentiment tier.

Deterministic, zero-cost, millisecond-fast lexicon analysis with negation
and intensifier handling. Gemini acts as a *secondary* cross-check one tier
up (see orchestration/pipeline.py); this module is what production serves
when the local path is authoritative.

Design notes
------------
* Handles negation windows ("not good", "never received") and intensifiers
  ("very bad", "slightly late") — the two constructs that break naive
  keyword counting.
* Strong multi-word phrases are matched first so "working now" wins over
  the individual tokens ("working" is absent from the lexicon on purpose —
  bare present participles are too ambiguous).
* Score is the *magnitude* of the winning polarity (0.55–0.95), mirroring
  the shape of the Gemini score so downstream consumers treat both tiers
  identically. No hits → NEUTRAL 0.5.
"""

import math
import re

from ml_service.api.schemas import SentimentLabel, SentimentResult

# Multi-word phrases first (highest precedence). (pattern, weight)
_PHRASES: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"\bworking\s+now\b|\bfixed\s+now\b|\ball\s+(is\s+)?good\b", re.I), 3.0),
    (re.compile(r"\bthank(s| you)\b", re.I), 2.0),
    (re.compile(r"\bnever\s+again\b|\bfed\s+up\b|\bwaste\s+of\b|\bdisgust(ing|ed)\b", re.I), -3.0),
    (re.compile(r"\bstill\s+waiting\b|\bno\s+(update|response|reply)\b", re.I), -2.0),
    (re.compile(r"\b(hasn'?t|have\s+not|did\s+not|didn'?t|not)\s+(arrived|received?|come|delivered)\b", re.I), -2.5),
    (re.compile(r"\bnobody\s+(replies|responds|answers)\b|\bno\s+one\s+(replies|responds|answers)\b", re.I), -2.0),
    (re.compile(r"\bcharged\s+(twice|double)\b|\bover\s?charged\b", re.I), -2.5),
    (re.compile(r"\bprompt(ly)?\s+(service|response|delivery|refund)\b", re.I), 2.5),
]

_POSITIVE: dict[str, float] = {
    "good": 1.5, "great": 2.0, "excellent": 2.5, "amazing": 2.5, "awesome": 2.5,
    "fantastic": 2.5, "wonderful": 2.5, "perfect": 2.5, "love": 2.5, "loved": 2.5,
    "lovely": 2.0, "happy": 2.0, "glad": 2.0, "pleased": 2.0, "satisfied": 2.0,
    "thanks": 1.5, "thank": 1.5, "helpful": 2.0, "helped": 1.5, "fast": 1.5,
    "quick": 1.5, "quickly": 1.5, "prompt": 1.5, "reliable": 2.0, "smooth": 1.5,
    "easy": 1.5, "resolved": 2.0, "fixed": 2.0, "appreciate": 2.0, "appreciated": 2.0,
    "impressed": 2.0, "recommend": 1.5, "best": 2.0, "polite": 1.5, "professional": 1.5,
    "friendly": 1.5, "efficient": 2.0, "nice": 1.5, "outstanding": 2.5, "superb": 2.5,
    "brilliant": 2.5, "flawless": 2.5, "seamless": 2.0, "responsive": 1.5,
    "courteous": 1.5, "worth": 1.0, "comfortable": 1.0, "quality": 1.0, "works": 1.5,
}

_NEGATIVE: dict[str, float] = {
    "bad": -1.5, "worst": -3.0, "terrible": -2.5, "horrible": -2.5, "awful": -2.5,
    "poor": -1.5, "hate": -2.5, "hated": -2.5, "angry": -2.0, "furious": -3.0,
    "frustrated": -2.0, "frustrating": -2.0, "annoyed": -1.5, "annoying": -1.5,
    "upset": -2.0, "disappointing": -2.0, "disappointed": -2.0, "broken": -1.5,
    "crash": -1.5, "crashes": -1.5, "crashed": -1.5, "bug": -1.0, "buggy": -1.5,
    "error": -1.0, "failed": -1.5, "failure": -1.5, "fails": -1.5, "issue": -0.5,
    "problem": -0.5, "problems": -0.5, "delayed": -1.0, "delay": -1.0, "late": -1.0,
    "missing": -1.5, "lost": -1.5, "damaged": -1.5, "defective": -2.0, "faulty": -2.0,
    "scam": -3.0, "fraud": -2.5, "phishing": -2.5, "hacked": -2.5, "stolen": -2.5,
    "unauthorized": -2.0, "overcharged": -2.0, "charged": -0.5, "deducted": -0.5,
    "refund": -0.5, "unprofessional": -2.0, "rude": -2.0, "useless": -2.5,
    "pathetic": -2.5, "pathetically": -2.5, "cheated": -2.5, "cheating": -2.0,
    "lied": -2.0, "lying": -2.0, "ignored": -1.5, "ignoring": -1.5, "waiting": -1.0,
    "pending": -0.5, "inconvenience": -1.0, "sucks": -2.5, "garbage": -2.5,
    "trash": -2.0, "unacceptable": -2.0, "ridiculous": -1.5, "expensive": -0.5,
}

_NEGATORS = {"not", "no", "never", "hardly", "barely", "cannot", "cant", "can't",
             "dont", "don't", "didnt", "didn't", "wasnt", "wasn't", "isnt", "isn't",
             "wont", "won't", "wouldnt", "wouldn't", "couldnt", "couldn't",
             "shouldnt", "shouldn't", "without", "unable"}

_INTENSIFIERS = {"very": 1.5, "extremely": 1.8, "really": 1.4, "so": 1.3,
                 "totally": 1.6, "absolutely": 1.7, "completely": 1.6,
                 "super": 1.5, "incredibly": 1.8, "highly": 1.5}
_DIMINISHERS = {"slightly": 0.5, "somewhat": 0.6, "fairly": 0.7, "bit": 0.6}

_TOKEN_RE = re.compile(r"[a-z']+")


def analyze_sentiment(message: str | None, subject: str | None = None) -> SentimentResult:
    """Lexicon+NLP sentiment: deterministic, provider="local", always available."""
    text = f"{subject or ''} {message or ''}".strip()
    if not text:
        return SentimentResult(
            label=SentimentLabel.NEUTRAL,
            score=0.5,
            reason="No content provided.",
            provider="local",
            available=True,
        )

    raw_score = 0.0
    matched: list[str] = []

    # 1. Phrase pass (overrides naive token hits for the same span)
    for pattern, weight in _PHRASES:
        m = pattern.search(text)
        if m:
            raw_score += weight
            matched.append(m.group(0).lower())

    # 2. Token pass with negation window + intensifiers
    tokens = _TOKEN_RE.findall(text.lower())
    for i, tok in enumerate(tokens):
        weight = _POSITIVE.get(tok) or _NEGATIVE.get(tok)
        if weight is None:
            continue
        window = tokens[max(0, i - 3):i]
        if any(n in _NEGATORS for n in window):
            weight = -weight  # "not good" → negative
        mult = 1.0
        if any(n in _INTENSIFIERS for n in window):
            mult = max(_INTENSIFIERS[n] for n in window if n in _INTENSIFIERS)
        elif any(n in _DIMINISHERS for n in window):
            mult = _DIMINISHERS[next(n for n in window if n in _DIMINISHERS)]
        raw_score += weight * mult
        matched.append(("not " if any(n in _NEGATORS for n in window) else "") + tok)

    if raw_score >= 1.0:
        label = SentimentLabel.POSITIVE
        magnitude = raw_score
    elif raw_score <= -1.0:
        label = SentimentLabel.NEGATIVE
        magnitude = -raw_score
    else:
        label = SentimentLabel.NEUTRAL
        magnitude = abs(raw_score)

    # Magnitude → 0.55–0.95 band (mirrors the Gemini score shape); neutral 0.5
    if label == SentimentLabel.NEUTRAL:
        score = 0.5
    else:
        score = round(0.55 + 0.4 * min(1.0, math.tanh(magnitude / 4.0)), 4)

    if matched:
        seen: list[str] = []
        for m in matched:
            if m not in seen:
                seen.append(m)
        reason = f"Lexicon signals ({label.value.lower()}): {', '.join(seen[:5])}"
    else:
        reason = "No sentiment-bearing terms detected."

    return SentimentResult(
        label=label,
        score=score,
        reason=reason,
        provider="local",
        available=True,
    )


class LocalNLPSentimentAnalyzer:
    """Class wrapper so the analyzer is swappable with the Gemini tier."""

    def analyze(self, message: str | None, subject: str | None = None) -> SentimentResult:
        return analyze_sentiment(message, subject)
