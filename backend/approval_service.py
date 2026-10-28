"""Human Approval and Simulated Sending Service.

Enforces human-in-the-loop review policies:
- Drafts require explicit human approval before they can be sent.
- Editing an approved draft automatically invalidates approval and resets status to PENDING_APPROVAL.
- Rejected or unapproved drafts cannot be sent.
- Simulates external email dispatch without connecting to third-party APIs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from backend.database import (
    get_draft_by_id,
    get_email_by_id,
    log_activity,
    update_draft_body,
    update_draft_status,
    update_email_status,
)


def can_send_draft(draft_id: int, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """Checks whether a draft is eligible for dispatch.

    Returns:
        Tuple of (allowed: bool, reason_message: str).
    """
    draft = get_draft_by_id(draft_id, db_path=db_path)
    if not draft:
        return False, f"Draft #{draft_id} not found."

    status = draft.get("status")
    if status == "SENT":
        return False, f"Draft #{draft_id} has already been sent."
    if status == "REJECTED":
        return False, f"Draft #{draft_id} was rejected and cannot be sent."
    if status == "PENDING_APPROVAL":
        return False, f"Draft #{draft_id} is pending human review and must be approved before sending."
    if status == "APPROVED":
        return True, "Draft is approved and ready for dispatch."

    return False, f"Invalid draft status: {status}"


def approve_draft(
    draft_id: int,
    reviewer_name: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Approves a draft response for dispatch.

    Args:
        draft_id: The primary key of the draft.
        reviewer_name: Name or ID of the human reviewer.
        db_path: Optional database path.

    Returns:
        Dict with status result.
    """
    draft = get_draft_by_id(draft_id, db_path=db_path)
    if not draft:
        return {"success": False, "error": f"Draft #{draft_id} does not exist."}

    if draft["status"] == "SENT":
        return {"success": False, "error": "Cannot modify an already sent draft."}

    cleaned_reviewer = reviewer_name.strip() or "Support Agent"
    success = update_draft_status(
        draft_id=draft_id,
        status="APPROVED",
        approved_by=cleaned_reviewer,
        db_path=db_path,
    )

    if success:
        log_activity(
            action="DRAFT_APPROVED",
            email_id=draft["email_id"],
            draft_id=draft_id,
            details=f"Approved by {cleaned_reviewer}",
            db_path=db_path,
        )
        return {
            "success": True,
            "status": "APPROVED",
            "approved_by": cleaned_reviewer,
            "message": f"Draft #{draft_id} successfully approved by {cleaned_reviewer}.",
        }

    return {"success": False, "error": "Database update failed."}


def reject_draft(
    draft_id: int,
    reviewer_name: str,
    reason: str = "",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Rejects a draft response.

    Args:
        draft_id: The primary key of the draft.
        reviewer_name: Name of reviewer rejecting the draft.
        reason: Optional justification for rejection.
        db_path: Optional database path.
    """
    draft = get_draft_by_id(draft_id, db_path=db_path)
    if not draft:
        return {"success": False, "error": f"Draft #{draft_id} does not exist."}

    if draft["status"] == "SENT":
        return {"success": False, "error": "Cannot reject an already sent draft."}

    cleaned_reviewer = reviewer_name.strip() or "Support Agent"
    success = update_draft_status(
        draft_id=draft_id,
        status="REJECTED",
        approved_by=None,
        db_path=db_path,
    )

    if success:
        log_activity(
            action="DRAFT_REJECTED",
            email_id=draft["email_id"],
            draft_id=draft_id,
            details=f"Rejected by {cleaned_reviewer}. Reason: {reason or 'No reason provided'}",
            db_path=db_path,
        )
        return {
            "success": True,
            "status": "REJECTED",
            "message": f"Draft #{draft_id} was rejected by {cleaned_reviewer}.",
        }

    return {"success": False, "error": "Database update failed."}


def edit_draft_content(
    draft_id: int,
    new_body: str,
    editor_name: str = "Support Agent",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Updates draft text and strictly invalidates approval status.

    CRITICAL RULE: Editing any draft automatically sets status to PENDING_APPROVAL
    and clears approved_by, requiring re-approval.
    """
    draft = get_draft_by_id(draft_id, db_path=db_path)
    if not draft:
        return {"success": False, "error": f"Draft #{draft_id} does not exist."}

    if draft["status"] == "SENT":
        return {"success": False, "error": "Cannot edit a draft that has already been dispatched."}

    if not new_body.strip():
        return {"success": False, "error": "Draft body cannot be empty."}

    was_approved = (draft["status"] == "APPROVED")
    success = update_draft_body(draft_id, new_body, db_path=db_path)

    if success:
        detail_msg = f"Draft edited by {editor_name}."
        if was_approved:
            detail_msg += " Prior approval was invalidated; re-approval required."

        log_activity(
            action="DRAFT_EDITED",
            email_id=draft["email_id"],
            draft_id=draft_id,
            details=detail_msg,
            db_path=db_path,
        )

        return {
            "success": True,
            "status": "PENDING_APPROVAL",
            "invalidated_approval": was_approved,
            "message": "Draft updated successfully. Status reset to PENDING_APPROVAL.",
        }

    return {"success": False, "error": "Database update failed."}


def simulate_send_draft(
    draft_id: int,
    sender_identity: str = "Support Automated Dispatcher",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Simulates sending an approved draft to the customer.

    CRITICAL RULE: Strictly blocks sending if draft is not APPROVED.
    """
    allowed, reason = can_send_draft(draft_id, db_path=db_path)
    if not allowed:
        return {
            "success": False,
            "error": reason,
        }

    draft = get_draft_by_id(draft_id, db_path=db_path)
    if not draft:
        return {"success": False, "error": "Draft not found."}

    email_id = draft["email_id"]
    email_record = get_email_by_id(email_id, db_path=db_path)
    recipient = email_record["sender"] if email_record else "customer@example.com"
    subject = f"Re: {email_record['subject']}" if email_record else "Support Response"

    now = datetime.now().isoformat()

    # 1. Update draft status to SENT
    draft_updated = update_draft_status(
        draft_id=draft_id,
        status="SENT",
        approved_by=draft.get("approved_by"),
        sent_at=now,
        db_path=db_path,
    )

    # 2. Update parent email status to REPLIED
    email_updated = update_email_status(email_id, "REPLIED", db_path=db_path)

    if draft_updated and email_updated:
        log_activity(
            action="EMAIL_SENT_SIMULATED",
            email_id=email_id,
            draft_id=draft_id,
            details=f"Simulated sending to {recipient} by {sender_identity}",
            db_path=db_path,
        )

        return {
            "success": True,
            "status": "SENT",
            "dispatch_receipt": {
                "recipient": recipient,
                "subject": subject,
                "sent_at": now,
                "dispatcher": sender_identity,
                "approved_by": draft.get("approved_by"),
                "body_preview": draft["draft_body"][:200] + ("..." if len(draft["draft_body"]) > 200 else ""),
            },
            "message": f"Draft #{draft_id} simulated send to {recipient} succeeded.",
        }

    return {"success": False, "error": "Failed to update database records for simulated sending."}
