"""Unit tests for Draft Response Generator (backend/draft_generator.py)."""

import pytest
from backend.database import init_db, insert_kb_article
from backend.draft_generator import generate_support_draft


@pytest.fixture
def draft_test_db(tmp_path):
    """Initializes a temporary database with seed KB articles."""
    db_file = str(tmp_path / "test_draft_db.db")
    init_db(db_file, seed_kb=False)

    insert_kb_article(
        {
            "title": "Application Crash Fix",
            "category": "Technical Support",
            "content": "Clear your client cache and update graphic drivers. Log file is at %APPDATA%/logs.",
            "tags": "crash, bug, client, freeze",
            "is_approved": 1,
        },
        db_path=db_file,
    )
    return db_file


def test_draft_generation_with_matched_kb(draft_test_db):
    """Verifies that draft incorporates the KB article solution when available."""
    res = generate_support_draft(
        sender="sarah.connor@example.com",
        subject="Application crash on launch",
        body="My client application crashes whenever I launch it.",
        category="Technical Support",
        urgency="High",
        team="Tier 2 / Tech Support",
        risk_flag=0,
        db_path=draft_test_db,
    )
    assert res["status"] == "PENDING_APPROVAL"
    assert res["used_kb"] is True
    assert "Sarah" in res["draft_body"]
    assert "Application Crash Fix" in res["draft_body"]
    assert "Clear your client cache" in res["draft_body"]
    assert "Tier 2 / Tech Support" in res["draft_body"]


def test_draft_generation_fallback_without_kb(draft_test_db):
    """Verifies fallback draft behavior when no KB article matches."""
    res = generate_support_draft(
        sender="david@unknown.org",
        subject="Very obscure proprietary integration question",
        body="How do I connect your system to a 1980s mainframe punch card reader?",
        category="General Inquiry",
        urgency="Low",
        team="Tier 1 Support",
        risk_flag=0,
        db_path=draft_test_db,
    )
    assert res["status"] == "PENDING_APPROVAL"
    assert res["used_kb"] is False
    assert "David" in res["draft_body"]
    assert "We have logged your request" in res["draft_body"]
    assert "Tier 1 Support" in res["draft_body"]


def test_draft_generation_with_risk_flag(draft_test_db):
    """Verifies that critical risk prompts an apologetic and prioritized opening."""
    res = generate_support_draft(
        sender="angry_client@corp.com",
        subject="Disaster: server outage",
        body="Our production is completely broken and we want to cancel our subscription!",
        category="Technical Support",
        urgency="Critical",
        team="Executive Escalations",
        risk_flag=1,
        risk_reason="Customer Churn Risk",
        db_path=draft_test_db,
    )
    assert res["status"] == "PENDING_APPROVAL"
    assert "apologize for the disruption" in res["draft_body"]
    assert "flagged with critical priority" in res["draft_body"]
    assert "Executive Escalations" in res["draft_body"]
