"""Unit tests for SQLite Database Layer (backend/database.py)."""

import os
import pytest
from backend.database import (
    init_db,
    insert_email,
    get_email_by_id,
    get_all_emails,
    update_email_status,
    update_email_metadata,
    insert_kb_article,
    get_kb_article_by_id,
    get_all_kb_articles,
    update_kb_article,
    delete_kb_article,
    insert_draft,
    get_draft_by_id,
    get_all_drafts,
    update_draft_body,
    update_draft_status,
    log_activity,
    get_activity_logs,
    get_summary_stats,
)


@pytest.fixture
def test_db(tmp_path):
    """Fixture that creates and initializes an isolated temporary SQLite database."""
    db_file = str(tmp_path / "test_support.db")
    init_db(db_file, seed_kb=True)
    return db_file


def test_db_initialization_and_seeding(test_db):
    """Verifies that tables are created and initial KB articles are seeded."""
    kb_articles = get_all_kb_articles(approved_only=True, db_path=test_db)
    assert len(kb_articles) >= 5
    assert any(a["category"] == "Technical Support" for a in kb_articles)
    assert any(a["category"] == "Billing & Payments" for a in kb_articles)


def test_email_crud(test_db):
    """Verifies email creation, retrieval, filtering, and status updates."""
    email_data = {
        "sender": "customer@example.com",
        "subject": "System crash on startup",
        "body": "Whenever I launch the app, it crashes with error code 500.",
        "category": "Technical Support",
        "urgency": "High",
        "team": "Tier 2 Support",
        "risk_flag": 0,
        "risk_reason": "",
        "status": "NEW",
    }
    email_id = insert_email(email_data, db_path=test_db)
    assert email_id > 0

    fetched = get_email_by_id(email_id, db_path=test_db)
    assert fetched is not None
    assert fetched["sender"] == "customer@example.com"
    assert fetched["subject"] == "System crash on startup"
    assert fetched["urgency"] == "High"

    # Status update
    assert update_email_status(email_id, "PROCESSED", db_path=test_db)
    updated = get_email_by_id(email_id, db_path=test_db)
    assert updated["status"] == "PROCESSED"

    # Metadata update
    assert update_email_metadata(email_id, "Technical Support", "Critical", "Tier 2 Support", 1, "Crash", db_path=test_db)
    meta_updated = get_email_by_id(email_id, db_path=test_db)
    assert meta_updated["urgency"] == "Critical"
    assert meta_updated["risk_flag"] == 1

    # Filtered retrieval
    all_emails = get_all_emails(status="PROCESSED", db_path=test_db)
    assert len(all_emails) == 1
    assert all_emails[0]["id"] == email_id


def test_kb_crud(test_db):
    """Verifies inserting, updating, searching, and deleting KB articles."""
    art_id = insert_kb_article(
        {
            "title": "Custom Test Article",
            "category": "General Inquiry",
            "content": "This is a custom test solution.",
            "tags": "test, custom",
            "is_approved": 1,
        },
        db_path=test_db,
    )
    assert art_id > 0

    art = get_kb_article_by_id(art_id, db_path=test_db)
    assert art["title"] == "Custom Test Article"

    # Update
    assert update_kb_article(art_id, "Updated Custom Article", "General Inquiry", "New content", "test", 1, db_path=test_db)
    art_updated = get_kb_article_by_id(art_id, db_path=test_db)
    assert art_updated["title"] == "Updated Custom Article"

    # Delete
    assert delete_kb_article(art_id, db_path=test_db)
    assert get_kb_article_by_id(art_id, db_path=test_db) is None


def test_draft_crud_and_invalidation(test_db):
    """Verifies draft creation, editing resets to PENDING_APPROVAL, and status transitions."""
    email_id = insert_email(
        {
            "sender": "user@test.org",
            "subject": "Need invoice",
            "body": "Please send me my latest invoice.",
            "category": "Billing & Payments",
            "urgency": "Low",
            "team": "Billing Team",
        },
        db_path=test_db,
    )

    draft_id = insert_draft(
        {
            "email_id": email_id,
            "draft_body": "Hello, here is how you can download your invoice...",
            "kb_article_ids": "1",
            "status": "PENDING_APPROVAL",
        },
        db_path=test_db,
    )
    assert draft_id > 0

    # Mark as APPROVED
    assert update_draft_status(draft_id, "APPROVED", approved_by="Agent Alice", db_path=test_db)
    draft = get_draft_by_id(draft_id, db_path=test_db)
    assert draft["status"] == "APPROVED"
    assert draft["approved_by"] == "Agent Alice"

    # Editing the draft body MUST invalidate approval and reset status to PENDING_APPROVAL
    assert update_draft_body(draft_id, "Hello, revised instructions...", db_path=test_db)
    draft_after_edit = get_draft_by_id(draft_id, db_path=test_db)
    assert draft_after_edit["status"] == "PENDING_APPROVAL"
    assert draft_after_edit["approved_by"] is None
    assert "revised" in draft_after_edit["draft_body"]


def test_activity_log_and_stats(test_db):
    """Verifies audit logging and summary metrics."""
    log_id = log_activity("TEST_ACTION", details="Testing the log feature", db_path=test_db)
    assert log_id > 0

    logs = get_activity_logs(limit=10, db_path=test_db)
    assert any(l["action"] == "TEST_ACTION" for l in logs)

    stats = get_summary_stats(db_path=test_db)
    assert "total_emails" in stats
    assert "kb_articles_count" in stats
    assert stats["kb_articles_count"] >= 5
