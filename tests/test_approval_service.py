"""Unit tests for Human Approval and Simulated Sending (backend/approval_service.py)."""

import pytest
from backend.database import init_db, insert_email, insert_draft, get_draft_by_id, get_email_by_id
from backend.approval_service import (
    approve_draft,
    reject_draft,
    edit_draft_content,
    simulate_send_draft,
    can_send_draft,
)


@pytest.fixture
def approval_db(tmp_path):
    """Fixture that initializes a clean DB and returns an email and draft ID."""
    db_file = str(tmp_path / "test_approval.db")
    init_db(db_file, seed_kb=False)

    email_id = insert_email(
        {
            "sender": "client@enterprise.com",
            "subject": "System crash",
            "body": "Application crashes every time I load data.",
            "category": "Technical Support",
            "urgency": "High",
            "team": "Tier 2 / Tech Support",
            "status": "NEW",
        },
        db_path=db_file,
    )

    draft_id = insert_draft(
        {
            "email_id": email_id,
            "draft_body": "Hello client, please clear cache and try again.",
            "status": "PENDING_APPROVAL",
        },
        db_path=db_file,
    )

    return db_file, email_id, draft_id


def test_draft_requires_approval_before_sending(approval_db):
    """Verifies that unapproved drafts cannot be dispatched."""
    db_file, _, draft_id = approval_db
    allowed, reason = can_send_draft(draft_id, db_path=db_file)
    assert allowed is False
    assert "must be approved" in reason

    res = simulate_send_draft(draft_id, db_path=db_file)
    assert res["success"] is False
    assert "error" in res


def test_approve_draft_and_send(approval_db):
    """Verifies standard approval workflow leading to simulated send."""
    db_file, email_id, draft_id = approval_db

    # 1. Approve draft
    app_res = approve_draft(draft_id, reviewer_name="Agent Viraj", db_path=db_file)
    assert app_res["success"] is True
    assert app_res["status"] == "APPROVED"

    draft = get_draft_by_id(draft_id, db_path=db_file)
    assert draft["status"] == "APPROVED"
    assert draft["approved_by"] == "Agent Viraj"

    # 2. Can send
    allowed, _ = can_send_draft(draft_id, db_path=db_file)
    assert allowed is True

    # 3. Simulate send
    send_res = simulate_send_draft(draft_id, sender_identity="Viraj Dispatcher", db_path=db_file)
    assert send_res["success"] is True
    assert send_res["status"] == "SENT"
    assert send_res["dispatch_receipt"]["recipient"] == "client@enterprise.com"

    # Verify database state after send
    sent_draft = get_draft_by_id(draft_id, db_path=db_file)
    assert sent_draft["status"] == "SENT"
    assert sent_draft["sent_at"] is not None

    email = get_email_by_id(email_id, db_path=db_file)
    assert email["status"] == "REPLIED"


def test_editing_approved_draft_invalidates_approval(approval_db):
    """CRITICAL TEST: Editing an approved draft must reset status to PENDING_APPROVAL."""
    db_file, _, draft_id = approval_db

    # First approve it
    approve_draft(draft_id, reviewer_name="Supervisor Bob", db_path=db_file)
    draft_before = get_draft_by_id(draft_id, db_path=db_file)
    assert draft_before["status"] == "APPROVED"

    # Now edit draft body
    edit_res = edit_draft_content(
        draft_id,
        new_body="Updated: Please restart in safe mode first.",
        editor_name="Agent Carol",
        db_path=db_file,
    )
    assert edit_res["success"] is True
    assert edit_res["status"] == "PENDING_APPROVAL"
    assert edit_res["invalidated_approval"] is True

    # Check database: status must be PENDING_APPROVAL, approved_by must be cleared
    draft_after = get_draft_by_id(draft_id, db_path=db_file)
    assert draft_after["status"] == "PENDING_APPROVAL"
    assert draft_after["approved_by"] is None

    # Sending must now fail
    allowed, _ = can_send_draft(draft_id, db_path=db_file)
    assert allowed is False


def test_rejected_draft_cannot_be_sent(approval_db):
    """Verifies that rejected drafts cannot be marked as sent."""
    db_file, _, draft_id = approval_db

    rej_res = reject_draft(draft_id, reviewer_name="Supervisor Bob", reason="Inaccurate advice", db_path=db_file)
    assert rej_res["success"] is True
    assert rej_res["status"] == "REJECTED"

    draft = get_draft_by_id(draft_id, db_path=db_file)
    assert draft["status"] == "REJECTED"

    # Cannot send rejected draft
    allowed, reason = can_send_draft(draft_id, db_path=db_file)
    assert allowed is False
    assert "rejected" in reason

    send_res = simulate_send_draft(draft_id, db_path=db_file)
    assert send_res["success"] is False


def test_sent_draft_cannot_be_edited_or_resent(approval_db):
    """Verifies immutable state once sent."""
    db_file, _, draft_id = approval_db

    approve_draft(draft_id, reviewer_name="Supervisor Bob", db_path=db_file)
    simulate_send_draft(draft_id, db_path=db_file)

    # Attempting to edit sent draft
    edit_res = edit_draft_content(draft_id, "Attempted revision", db_path=db_file)
    assert edit_res["success"] is False

    # Attempting to re-send
    send_again = simulate_send_draft(draft_id, db_path=db_file)
    assert send_again["success"] is False
