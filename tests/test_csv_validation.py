"""Unit tests for CSV Validation and Batch Intake (backend/email_processor.py)."""

import os
import pytest
from backend.database import init_db, get_all_emails, get_all_drafts
from backend.email_processor import validate_csv_content, import_emails_from_csv


@pytest.fixture
def csv_test_db(tmp_path):
    """Initializes a temporary database for CSV import testing."""
    db_file = str(tmp_path / "test_csv.db")
    init_db(db_file, seed_kb=True)
    return db_file


def test_validate_csv_success():
    """Verifies that valid CSV content passes validation."""
    valid_csv = "sender,subject,body\nuser@test.com,Password issue,Cannot login"
    is_valid, errors = validate_csv_content(valid_csv)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_csv_missing_columns():
    """Verifies rejection when mandatory columns are missing."""
    invalid_csv = "email,title\nuser@test.com,Cannot login"
    is_valid, errors = validate_csv_content(invalid_csv)
    assert is_valid is False
    assert any("Missing mandatory CSV columns" in e for e in errors)


def test_import_csv_with_malformed_and_valid_rows(csv_test_db):
    """Verifies that valid rows are imported while malformed rows are gracefully skipped."""
    csv_data = (
        "sender,subject,body\n"
        "valid.user@example.com,Crashing app,Application throws error 500 on launch\n"
        "invalid_email_no_at,Subject text,Some body content\n"  # Invalid email
        "user2@test.com,,Empty subject line\n"                 # Missing subject
        "user3@test.com,Refund request,Please refund my monthly subscription\n" # Valid
    )

    res = import_emails_from_csv(csv_data, db_path=csv_test_db)
    assert res["total_rows"] == 4
    assert res["imported_count"] == 2
    assert res["skipped_count"] == 2
    assert len(res["errors"]) == 2

    # Verify database contents
    emails = get_all_emails(db_path=csv_test_db)
    assert len(emails) == 2
    drafts = get_all_drafts(db_path=csv_test_db)
    assert len(drafts) == 2


def test_import_sample_emails_csv(csv_test_db):
    """Verifies batch import from data/sample_emails.csv."""
    sample_csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "sample_emails.csv",
    )
    assert os.path.exists(sample_csv_path)

    res = import_emails_from_csv(sample_csv_path, db_path=csv_test_db)
    assert res["imported_count"] >= 10
    assert res["skipped_count"] == 0

    emails = get_all_emails(db_path=csv_test_db)
    assert len(emails) == res["imported_count"]

    # Verify risk detection occurred
    risk_emails = [e for e in emails if e["risk_flag"] == 1]
    assert len(risk_emails) >= 1
