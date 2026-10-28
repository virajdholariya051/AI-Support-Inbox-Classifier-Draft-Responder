"""Support Team Assignment Routing Matrix.

Assigns incoming support tickets to specialized operational teams based on
predicted category, urgency level, and risk presence.
"""

from __future__ import annotations

from typing import Any, Dict

# Standard Support Teams
TEAMS = [
    "Tier 1 Support",
    "Tier 2 / Tech Support",
    "Billing Team",
    "Accounts & Security",
    "Product Management",
    "Executive Escalations",
]


def assign_support_team(
    category: str,
    urgency: str = "Low",
    risk_flag: int = 0,
) -> Dict[str, Any]:
    """Determines the appropriate operational support team and handling priority.

    Args:
        category: Email category (e.g., 'Technical Support', 'Billing & Payments', etc.).
        urgency: Urgency level ('Low', 'Medium', 'High', 'Critical').
        risk_flag: 1 if churn/legal risk is detected, else 0.

    Returns:
        Dict containing assigned 'team', 'sla_hours', and 'assignment_reason'.
    """
    # 1. High risk or Critical urgency escalation overrides
    if risk_flag == 1 and urgency in ("High", "Critical"):
        return {
            "team": "Executive Escalations",
            "sla_hours": 1,
            "assignment_reason": "Escalated due to high customer churn or legal/compliance risk flag.",
        }

    # 2. Category-based routing
    if category == "Technical Support":
        if urgency in ("High", "Critical"):
            team = "Tier 2 / Tech Support"
            sla_hours = 2 if urgency == "Critical" else 4
            reason = "Technical issue with elevated urgency assigned directly to Tier 2 engineering."
        else:
            team = "Tier 2 / Tech Support"
            sla_hours = 12
            reason = "Standard technical query routed to technical support desk."

    elif category == "Billing & Payments":
        team = "Billing Team"
        sla_hours = 4 if urgency in ("High", "Critical") else 16
        reason = "Payment or subscription issue routed to specialized billing team."

    elif category == "Account Access":
        team = "Accounts & Security"
        sla_hours = 2 if urgency in ("High", "Critical") else 8
        reason = "Login or credential security issue routed to Accounts & Security."

    elif category == "Feature Request":
        team = "Product Management"
        sla_hours = 48
        reason = "Product enhancement request queued for product management roadmap review."

    else:  # General Inquiry
        team = "Tier 1 Support"
        sla_hours = 24
        reason = "General inquiry routed to Tier 1 front-line support desk."

    return {
        "team": team,
        "sla_hours": sla_hours,
        "assignment_reason": reason,
    }
