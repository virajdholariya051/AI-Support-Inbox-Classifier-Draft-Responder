"""Unit tests for Knowledge Base Retrieval (backend/knowledge_base.py)."""

import pytest
from backend.database import init_db, insert_kb_article
from backend.knowledge_base import find_relevant_articles


@pytest.fixture
def kb_test_db(tmp_path):
    """Initializes a temporary database with approved and unapproved articles."""
    db_file = str(tmp_path / "test_kb.db")
    init_db(db_file, seed_kb=False)

    # Insert an approved article
    insert_kb_article(
        {
            "title": "Password Reset Procedures",
            "category": "Account Access",
            "content": "Follow the link on the login page to reset your security credentials and password.",
            "tags": "password, login, reset, credentials",
            "is_approved": 1,
        },
        db_path=db_file,
    )

    # Insert an UNAPPROVED article (Must NOT be retrieved for drafts)
    insert_kb_article(
        {
            "title": "Confidential Internal Debugging Password Override",
            "category": "Account Access",
            "content": "Internal bypass override tool only for engineering access.",
            "tags": "password, override, internal",
            "is_approved": 0,
        },
        db_path=db_file,
    )

    # Insert a billing article
    insert_kb_article(
        {
            "title": "Downloading VAT Invoices",
            "category": "Billing & Payments",
            "content": "Go to Settings -> Billing -> Invoices to download PDF receipts.",
            "tags": "invoice, billing, tax, vat, receipt",
            "is_approved": 1,
        },
        db_path=db_file,
    )

    return db_file


def test_approved_articles_retrieval(kb_test_db):
    """Verifies that relevant approved articles are matched."""
    results = find_relevant_articles(
        query_text="I forgot my account password and cannot log in",
        category="Account Access",
        approved_only=True,
        db_path=kb_test_db,
    )
    assert len(results) >= 1
    assert "Password Reset Procedures" in results[0]["title"]
    assert results[0]["relevance_score"] > 0.1


def test_unapproved_articles_are_never_retrieved(kb_test_db):
    """CRITICAL TEST: Ensures unapproved KB articles are strictly excluded."""
    results = find_relevant_articles(
        query_text="Confidential Internal Debugging Password Override",
        category="Account Access",
        approved_only=True,
        db_path=kb_test_db,
    )
    for art in results:
        assert art["is_approved"] == 1
        assert "Confidential Internal Debugging" not in art["title"]


def test_irrelevant_query_returns_empty(kb_test_db):
    """Verifies that queries with no matching topics return empty results."""
    results = find_relevant_articles(
        query_text="Astronomy astrophysics quantum computing telescope",
        category="General Inquiry",
        approved_only=True,
        db_path=kb_test_db,
    )
    assert len(results) == 0


def test_empty_query_returns_empty(kb_test_db):
    """Verifies that empty string query returns empty list."""
    results = find_relevant_articles("", approved_only=True, db_path=kb_test_db)
    assert results == []
