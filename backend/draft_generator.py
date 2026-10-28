"""Draft Response Generator for AI Support Inbox.

Generates structured, professional, and empathetic support drafts using retrieved
knowledge-base solutions or graceful fallback templates when guidance is unavailable.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from backend.knowledge_base import find_relevant_articles


def _extract_customer_name(sender_email: str) -> str:
    """Extracts a friendly name from an email address or defaults to Customer."""
    if not sender_email or "@" not in sender_email:
        return "Customer"
    local_part = sender_email.split("@")[0]
    # Clean up dots, underscores, numbers
    cleaned = re.sub(r"[._\d]+", " ", local_part).strip()
    words = cleaned.split()
    if words:
        return words[0].capitalize()
    return "Customer"


def generate_support_draft(
    sender: str,
    subject: str,
    body: str,
    category: str = "General Inquiry",
    urgency: str = "Low",
    team: str = "Tier 1 Support",
    risk_flag: int = 0,
    risk_reason: str = "",
    kb_articles: Optional[List[Dict[str, Any]]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates an email response draft using retrieved KB guidance or a standard fallback.

    Args:
        sender: Customer email address.
        subject: Subject of the customer ticket.
        body: Message body from the customer.
        category: Classified category.
        urgency: Urgency level ('Low', 'Medium', 'High', 'Critical').
        team: Assigned support team.
        risk_flag: 1 if risk detected, 0 otherwise.
        risk_reason: Risk description.
        kb_articles: Optional pre-fetched KB articles; if None, searches DB automatically.
        db_path: Optional database path.

    Returns:
        Dict with 'draft_body', 'kb_article_ids', 'used_kb', and 'status'.
    """
    customer_name = _extract_customer_name(sender)
    combined_query = f"{subject} {body}"

    # Retrieve approved articles if not provided
    if kb_articles is None:
        kb_articles = find_relevant_articles(
            query_text=combined_query,
            category=category,
            top_k=2,
            approved_only=True,
            db_path=db_path,
        )

    # Empathetic opening lines based on urgency and risk
    if risk_flag == 1 or urgency == "Critical":
        opening = (
            f"Dear {customer_name},\n\n"
            f"Thank you for contacting us. We deeply apologize for the disruption and frustration "
            f"this experience has caused. Your ticket has been flagged with critical priority for our "
            f"{team} and senior leadership."
        )
    elif urgency == "High":
        opening = (
            f"Hello {customer_name},\n\n"
            f"Thank you for reaching out to us. We understand this matter is time-sensitive, "
            f"and our {team} is prioritizing your request."
        )
    else:
        opening = (
            f"Hello {customer_name},\n\n"
            f"Thank you for contacting our support team regarding '{subject}'."
        )

    # Case 1: Relevant Knowledge Base Article Found
    if kb_articles and len(kb_articles) > 0:
        primary_kb = kb_articles[0]
        kb_ids = [str(a["id"]) for a in kb_articles if "id" in a]

        guidance_text = (
            f"\n\nBased on our official documentation regarding '{primary_kb.get('title')}', "
            f"here are the recommended resolution steps:\n\n"
            f"{primary_kb.get('content', '').strip()}\n\n"
            f"Please try the steps outlined above. If you encounter any further difficulties "
            f"or if this does not completely resolve your inquiry, simply reply directly to this email "
            f"and a specialist from {team} will continue working with you."
        )
        used_kb = True

    # Case 2: No Relevant KB Article Found (Graceful Fallback)
    else:
        kb_ids = []
        guidance_text = (
            f"\n\nWe have logged your request regarding '{category}' and our specialists in {team} "
            f"are actively reviewing the details you provided.\n\n"
            f"Because this requires dedicated investigation by our team, we will conduct a full review "
            f"and get back to you with a comprehensive update shortly."
        )
        used_kb = False

    # Closing sign-off
    closing = (
        f"\n\nWarm regards,\n"
        f"{team}\n"
        f"AI Support Desk"
    )

    draft_body = opening + guidance_text + closing

    return {
        "draft_body": draft_body,
        "kb_article_ids": ",".join(kb_ids),
        "used_kb": used_kb,
        "status": "PENDING_APPROVAL",
    }
