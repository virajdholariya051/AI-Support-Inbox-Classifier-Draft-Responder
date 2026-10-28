"""Urgency Detector for AI Support Inbox.

Evaluates email urgency based on critical keyword indicators, severity patterns,
structural emphasis (excessive capitalization, exclamation marks), and impact phrasing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

CRITICAL_INDICATORS = [
    "system outage",
    "outage",
    "server down",
    "service down",
    "production down",
    "system down",
    "data loss",
    "security breach",
    "ransomware",
    "hacked",
    "sev-1",
    "sev1",
    "critical emergency",
    "fatal crash",
    "all users blocked",
]

HIGH_INDICATORS = [
    "urgent",
    "urgently",
    "asap",
    "immediately",
    "right away",
    "blocking",
    "cannot access",
    "locked out",
    "deadline",
    "broken",
    "fail",
    "failed",
    "error 500",
    "production broken",
    "losing money",
    "unacceptable delay",
    "time sensitive",
]

MEDIUM_INDICATORS = [
    "issue",
    "problem",
    "trouble",
    "delay",
    "glitch",
    "not working",
    "slow",
    "latency",
    "charged twice",
    "wrong amount",
    "incorrect invoice",
    "expired",
]

LOW_INDICATORS = [
    "question",
    "wondering",
    "how to",
    "feature request",
    "suggestion",
    "feedback",
    "minor",
    "documentation",
    "general inquiry",
    "nice to have",
    "when possible",
    "thank you",
]


def detect_urgency(subject: str, body: str) -> Dict[str, Any]:
    """Calculates the urgency level (Low, Medium, High, Critical) and score (0-100).

    Args:
        subject: The email subject line.
        body: The email body text.

    Returns:
        Dict with 'urgency', 'score', and 'reasons'.
    """
    combined = f"{subject} {body}".strip()
    if not combined:
        return {
            "urgency": "Low",
            "score": 10,
            "reasons": ["Empty or blank message defaults to Low urgency"],
        }

    lower_text = combined.lower()
    score = 25  # Base score
    reasons: List[str] = []

    # 1. Check for Critical indicators (Weight +60)
    matched_critical = [term for term in CRITICAL_INDICATORS if term in lower_text]
    if matched_critical:
        score += 65
        reasons.append(f"Critical keywords identified: {', '.join(matched_critical)}")

    # 2. Check for High indicators (Weight +35)
    matched_high = [term for term in HIGH_INDICATORS if re.search(r"\b" + re.escape(term) + r"\b", lower_text)]
    if matched_high:
        score += 35
        reasons.append(f"High urgency phrasing: {', '.join(matched_high)}")

    # 3. Check for Medium indicators (Weight +15)
    matched_medium = [term for term in MEDIUM_INDICATORS if re.search(r"\b" + re.escape(term) + r"\b", lower_text)]
    if matched_medium:
        score += 15
        reasons.append(f"Issue indicators detected: {', '.join(matched_medium)}")

    # 4. Check for Low indicators (Weight -15)
    matched_low = [term for term in LOW_INDICATORS if re.search(r"\b" + re.escape(term) + r"\b", lower_text)]
    if matched_low and not matched_critical and not matched_high:
        score -= 15
        reasons.append(f"Informational / low-priority phrasing: {', '.join(matched_low)}")

    # 5. Tone & formatting emphasis modifiers
    # Multiple exclamation marks (e.g. "!!!" or "!!")
    if re.search(r"!{2,}", combined):
        score += 10
        reasons.append("Intense punctuation detected (repeated exclamation marks)")

    # All-caps words (e.g. "URGENT", "CRITICAL", "DOWN", "HELP")
    words = re.findall(r"\b[A-Z]{3,}\b", combined)
    urgent_caps = [w for w in words if w in {"URGENT", "EMERGENCY", "DOWN", "HELP", "NOW", "ASAP", "CRITICAL", "BROKEN"}]
    if urgent_caps:
        score += 15
        reasons.append(f"Capitalized stress words: {', '.join(set(urgent_caps))}")

    # Clamp score between 0 and 100
    score = max(0, min(100, score))

    # Map score to Urgency label
    if score >= 80 or matched_critical:
        urgency = "Critical"
    elif score >= 55 or (matched_high and score >= 45):
        urgency = "High"
    elif score >= 30:
        urgency = "Medium"
    else:
        urgency = "Low"

    if not reasons:
        reasons.append("Standard message tone with no elevated urgency signals")

    return {
        "urgency": urgency,
        "score": score,
        "reasons": reasons,
    }
