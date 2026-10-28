"""Email Processor and Batch Intake Pipeline.

Coordinates classification, urgency scoring, risk detection, team routing,
knowledge base matching, draft generation, and database storage for incoming emails.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.approval_service import log_activity
from backend.database import insert_draft, insert_email
from backend.draft_generator import generate_support_draft
from backend.email_classifier import classify_support_email
from backend.knowledge_base import find_relevant_articles
from backend.risk_detector import detect_risk
from backend.team_assignment import assign_support_team
from backend.urgency_detector import detect_urgency


def process_and_save_email(
    sender: str,
    subject: str,
    body: str,
    auto_generate_draft: bool = True,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs full analysis pipeline on an incoming email and saves records to SQLite.

    Pipeline Steps:
    1. Validate input text.
    2. Scikit-learn Category Classification.
    3. Urgency Detection & Scoring.
    4. Churn & Regulatory Risk Analysis.
    5. Team Routing & SLA calculation.
    6. Database Email Record Creation.
    7. Approved Knowledge Base Retrieval.
    8. Initial Draft Synthesis & Creation.

    Returns:
        Dict containing email_id, draft_id, classification, urgency, risk, team, and draft.
    """
    clean_sender = sender.strip()
    clean_subject = subject.strip()
    clean_body = body.strip()

    if not clean_sender or "@" not in clean_sender:
        raise ValueError("Invalid sender email address.")
    if not clean_subject:
        raise ValueError("Email subject cannot be empty.")
    if not clean_body:
        raise ValueError("Email body cannot be empty.")

    # 1. Classification
    class_res = classify_support_email(clean_subject, clean_body)
    category = class_res["category"]

    # 2. Urgency Detection
    urg_res = detect_urgency(clean_subject, clean_body)
    urgency = urg_res["urgency"]

    # 3. Risk Detection
    risk_res = detect_risk(clean_subject, clean_body)
    risk_flag = risk_res["risk_flag"]
    risk_reason = risk_res["risk_reason"]

    # 4. Team Assignment
    team_res = assign_support_team(category=category, urgency=urgency, risk_flag=risk_flag)
    assigned_team = team_res["team"]

    # 5. Insert Email into Database
    email_data = {
        "sender": clean_sender,
        "subject": clean_subject,
        "body": clean_body,
        "category": category,
        "urgency": urgency,
        "team": assigned_team,
        "risk_flag": risk_flag,
        "risk_reason": risk_reason,
        "status": "NEW",
    }
    email_id = insert_email(email_data, db_path=db_path)

    # 6. Retrieve relevant approved KB articles & generate response draft
    draft_id = None
    draft_data = None
    if auto_generate_draft:
        kb_matches = find_relevant_articles(
            query_text=f"{clean_subject} {clean_body}",
            category=category,
            top_k=2,
            approved_only=True,
            db_path=db_path,
        )

        draft_data = generate_support_draft(
            sender=clean_sender,
            subject=clean_subject,
            body=clean_body,
            category=category,
            urgency=urgency,
            team=assigned_team,
            risk_flag=risk_flag,
            risk_reason=risk_reason,
            kb_articles=kb_matches,
            db_path=db_path,
        )

        draft_id = insert_draft(
            {
                "email_id": email_id,
                "draft_body": draft_data["draft_body"],
                "kb_article_ids": draft_data["kb_article_ids"],
                "status": "PENDING_APPROVAL",
            },
            db_path=db_path,
        )

    return {
        "email_id": email_id,
        "draft_id": draft_id,
        "category": category,
        "confidence": class_res["confidence"],
        "urgency": urgency,
        "urgency_score": urg_res["score"],
        "team": assigned_team,
        "sla_hours": team_res["sla_hours"],
        "risk_flag": risk_flag,
        "risk_reason": risk_reason,
        "draft_body": draft_data["draft_body"] if draft_data else None,
        "used_kb": draft_data["used_kb"] if draft_data else False,
    }


def validate_csv_content(csv_file_or_content: Union[str, io.StringIO, io.BytesIO]) -> Tuple[bool, List[str]]:
    """Validates CSV structure and required header columns."""
    if isinstance(csv_file_or_content, bytes):
        text = csv_file_or_content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
    elif isinstance(csv_file_or_content, str):
        if "\n" in csv_file_or_content or "," in csv_file_or_content:
            reader = csv.DictReader(io.StringIO(csv_file_or_content))
        else:
            with open(csv_file_or_content, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
    elif hasattr(csv_file_or_content, "read"):
        raw = csv_file_or_content.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))
    else:
        return False, ["Unsupported file format or object."]

    headers = [h.strip().lower() for h in (reader.fieldnames or []) if h]
    required = {"sender", "subject", "body"}
    missing = required - set(headers)
    if missing:
        return False, [f"Missing mandatory CSV columns: {', '.join(sorted(missing))}"]

    return True, []


def import_emails_from_csv(
    csv_file_or_content: Union[str, io.StringIO, io.BytesIO],
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Parses a CSV file, validates rows, runs pipeline, and stores records in SQLite."""
    # Read text content
    if isinstance(csv_file_or_content, bytes):
        text = csv_file_or_content.decode("utf-8", errors="replace")
    elif isinstance(csv_file_or_content, str):
        if "\n" in csv_file_or_content or "," in csv_file_or_content:
            text = csv_file_or_content
        else:
            with open(csv_file_or_content, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
    elif hasattr(csv_file_or_content, "read"):
        raw = csv_file_or_content.read()
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    else:
        return {"total_rows": 0, "imported_count": 0, "skipped_count": 0, "errors": ["Invalid file type"]}

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip().lower() for h in (reader.fieldnames or []) if h]
    required = {"sender", "subject", "body"}
    missing = required - set(headers)
    if missing:
        return {
            "total_rows": 0,
            "imported_count": 0,
            "skipped_count": 0,
            "errors": [f"Missing required columns: {', '.join(sorted(missing))}"],
        }

    imported = 0
    skipped = 0
    errors: List[str] = []
    row_num = 1

    for row in reader:
        row_num += 1
        # Normalize keys
        norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        sender = norm_row.get("sender", "")
        subject = norm_row.get("subject", "")
        body = norm_row.get("body", "")

        if not sender or not subject or not body:
            skipped += 1
            errors.append(f"Row {row_num}: Skipped due to blank sender, subject, or body.")
            continue

        if "@" not in sender:
            skipped += 1
            errors.append(f"Row {row_num}: Skipped due to invalid sender email '{sender}'.")
            continue

        try:
            process_and_save_email(
                sender=sender,
                subject=subject,
                body=body,
                auto_generate_draft=True,
                db_path=db_path,
            )
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {row_num}: Error processing email ({e}).")

    return {
        "total_rows": row_num - 1,
        "imported_count": imported,
        "skipped_count": skipped,
        "errors": errors,
    }
