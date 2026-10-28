"""Risk Detector for AI Support Inbox.

Detects customer churn risks, legal/compliance liabilities, and severe escalation threats
using targeted semantic indicators and phrase patterns.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

CHURN_TRIGGERS = [
    "cancel subscription",
    "cancel my subscription",
    "cancel my account",
    "cancel service",
    "canceling",
    "cancelling",
    "closing our account",
    "close my account",
    "leave your platform",
    "switching to competitor",
    "switching to alternative",
    "moving to competitor",
    "demand full refund",
    "want my money back",
    "terrible product",
    "waste of money",
    "take our business elsewhere",
    "worthless service",
]

LEGAL_TRIGGERS = [
    "lawyer",
    "attorney",
    "lawsuit",
    "legal action",
    "sue you",
    "suing",
    "take you to court",
    "court action",
    "gdpr violation",
    "gdpr breach",
    "data breach",
    "privacy breach",
    "consumer protection",
    "report to authorities",
    "report to ftc",
    "fraudulent charge",
    "illegal",
    "compliance violation",
]

ESCALATION_TRIGGERS = [
    "unacceptable",
    "speak to manager",
    "speak to your manager",
    "talk to supervisor",
    "speak to ceo",
    "executive escalation",
    "escalate immediately",
    "taking this to twitter",
    "post on social media",
    "leave a 1 star review",
    "public review on trustpilot",
    "file a formal complaint",
    "completely dissatisfied",
]


def detect_risk(subject: str, body: str) -> Dict[str, Any]:
    """Analyzes email subject and body for churn, legal, and escalation risks.

    Args:
        subject: Email subject text.
        body: Email body text.

    Returns:
        Dict containing risk_flag (0 or 1), risk_score (0-100), risk_types,
        risk_reason (summary string), reasons list, and recommended_action.
    """
    combined = f"{subject} {body}".strip()
    if not combined:
        return {
            "risk_flag": 0,
            "risk_score": 0,
            "risk_types": [],
            "risk_reason": "No risk detected (empty message)",
            "reasons": [],
            "severity": "None",
            "recommended_action": "Standard ticket routing",
        }

    lower_text = combined.lower()
    risk_score = 0
    risk_types: List[str] = []
    reasons: List[str] = []

    # 1. Evaluate Legal & Compliance Triggers (+60 score)
    matched_legal = [
        term for term in LEGAL_TRIGGERS
        if re.search(r"\b" + re.escape(term) + r"\b", lower_text)
    ]
    if matched_legal:
        risk_score += 65
        risk_types.append("Legal / Compliance Risk")
        reasons.append(f"Legal threats or regulatory references detected: {', '.join(matched_legal)}")

    # 2. Evaluate Churn Triggers (+45 score)
    matched_churn = [
        term for term in CHURN_TRIGGERS
        if re.search(r"\b" + re.escape(term) + r"\b", lower_text)
    ]
    if matched_churn:
        risk_score += 45
        risk_types.append("Customer Churn Risk")
        reasons.append(f"Cancellation or competitor switching signals: {', '.join(matched_churn)}")

    # 3. Evaluate Escalation Triggers (+30 score)
    matched_esc = [
        term for term in ESCALATION_TRIGGERS
        if re.search(r"\b" + re.escape(term) + r"\b", lower_text)
    ]
    if matched_esc:
        risk_score += 30
        risk_types.append("Severe Escalation / Reputation Risk")
        reasons.append(f"Escalation or social reputation threat detected: {', '.join(matched_esc)}")

    # Clamp score
    risk_score = min(100, risk_score)
    risk_flag = 1 if risk_score >= 40 else 0

    if risk_score >= 75:
        severity = "Critical"
        recommended_action = "Immediate supervisory review and executive outreach within 1 hour."
    elif risk_score >= 40:
        severity = "High"
        recommended_action = "Prioritize retention outreach and review account history before replying."
    elif risk_score >= 20:
        severity = "Moderate"
        recommended_action = "Standard handling with heightened professional tone."
    else:
        severity = "None"
        recommended_action = "Standard ticket processing."

    summary_reason = "; ".join(risk_types) if risk_types else "No risk signals"

    return {
        "risk_flag": risk_flag,
        "risk_score": risk_score,
        "risk_types": risk_types,
        "risk_reason": summary_reason,
        "reasons": reasons,
        "severity": severity,
        "recommended_action": recommended_action,
    }
