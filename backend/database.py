"""SQLite Database Layer for AI Support Inbox Classifier & Draft Responder.

Handles database connection, schema creation, seeding, and all CRUD operations
with parameterized queries and integrity checks.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

# Default database location inside project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "support_inbox.db")
INITIAL_KB_PATH = os.path.join(PROJECT_ROOT, "data", "initial_kb.json")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates and returns an SQLite database connection with row factory enabled."""
    target_path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None, seed_kb: bool = True) -> None:
    """Initializes the database schema and seeds initial knowledge base articles."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    category TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    team TEXT NOT NULL,
                    risk_flag INTEGER NOT NULL DEFAULT 0,
                    risk_reason TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'NEW',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    is_approved INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER NOT NULL,
                    draft_body TEXT NOT NULL,
                    kb_article_ids TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
                    approved_by TEXT DEFAULT NULL,
                    sent_at TEXT DEFAULT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER DEFAULT NULL,
                    draft_id INTEGER DEFAULT NULL,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    timestamp TEXT NOT NULL
                );
                """
            )

        if seed_kb:
            _seed_knowledge_base(conn)
    finally:
        conn.close()


def _seed_knowledge_base(conn: sqlite3.Connection) -> None:
    """Populates knowledge base with default approved articles if table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM knowledge_base;")
    count = cursor.fetchone()[0]
    if count == 0 and os.path.exists(INITIAL_KB_PATH):
        try:
            with open(INITIAL_KB_PATH, "r", encoding="utf-8") as f:
                articles = json.load(f)
            now = datetime.now().isoformat()
            with conn:
                for art in articles:
                    conn.execute(
                        """
                        INSERT INTO knowledge_base (title, category, content, tags, is_approved, created_at)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (
                            art.get("title", ""),
                            art.get("category", "General Inquiry"),
                            art.get("content", ""),
                            art.get("tags", ""),
                            art.get("is_approved", 1),
                            now,
                        ),
                    )
        except Exception as e:
            print(f"Warning: Failed to seed knowledge base: {e}")


# ============================================================================
# Email CRUD
# ============================================================================

def insert_email(email_data: Dict[str, Any], db_path: Optional[str] = None) -> int:
    """Inserts a new support email and logs the action."""
    conn = get_connection(db_path)
    try:
        created_at = email_data.get("created_at") or datetime.now().isoformat()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO emails (sender, subject, body, category, urgency, team, risk_flag, risk_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    email_data["sender"],
                    email_data["subject"],
                    email_data["body"],
                    email_data.get("category", "General Inquiry"),
                    email_data.get("urgency", "Low"),
                    email_data.get("team", "Tier 1 Support"),
                    email_data.get("risk_flag", 0),
                    email_data.get("risk_reason", ""),
                    email_data.get("status", "NEW"),
                    created_at,
                ),
            )
            email_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO activity_logs (email_id, action, details, timestamp)
                VALUES (?, ?, ?, ?);
                """,
                (email_id, "EMAIL_CREATED", f"Received from {email_data['sender']}", created_at),
            )
        return int(email_id)
    finally:
        conn.close()


def get_email_by_id(email_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches a single email by its primary key ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM emails WHERE id = ?;", (email_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_emails(
    status: Optional[str] = None,
    category: Optional[str] = None,
    urgency: Optional[str] = None,
    search_query: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves all emails matching optional filter conditions."""
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM emails WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if urgency:
            query += " AND urgency = ?"
            params.append(urgency)
        if search_query:
            query += " AND (subject LIKE ? OR body LIKE ? OR sender LIKE ?)"
            term = f"%{search_query}%"
            params.extend([term, term, term])

        query += " ORDER BY id DESC;"
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def update_email_status(email_id: int, status: str, db_path: Optional[str] = None) -> bool:
    """Updates the status of an email."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE emails SET status = ? WHERE id = ?;",
                (status, email_id),
            )
            updated = cursor.rowcount > 0
            if updated:
                conn.execute(
                    """
                    INSERT INTO activity_logs (email_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?);
                    """,
                    (email_id, "STATUS_UPDATED", f"Status changed to {status}", datetime.now().isoformat()),
                )
            return updated
    finally:
        conn.close()


def update_email_metadata(
    email_id: int,
    category: str,
    urgency: str,
    team: str,
    risk_flag: int,
    risk_reason: str,
    db_path: Optional[str] = None,
) -> bool:
    """Updates classified metadata of an email."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE emails 
                SET category = ?, urgency = ?, team = ?, risk_flag = ?, risk_reason = ?
                WHERE id = ?;
                """,
                (category, urgency, team, risk_flag, risk_reason, email_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


# ============================================================================
# Knowledge Base CRUD
# ============================================================================

def insert_kb_article(article_data: Dict[str, Any], db_path: Optional[str] = None) -> int:
    """Inserts a new article into the knowledge base."""
    conn = get_connection(db_path)
    try:
        now = datetime.now().isoformat()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO knowledge_base (title, category, content, tags, is_approved, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    article_data["title"],
                    article_data.get("category", "General Inquiry"),
                    article_data["content"],
                    article_data.get("tags", ""),
                    article_data.get("is_approved", 1),
                    now,
                ),
            )
            art_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO activity_logs (action, details, timestamp)
                VALUES (?, ?, ?);
                """,
                ("KB_ARTICLE_ADDED", f"Added KB #{art_id}: {article_data['title']}", now),
            )
        return int(art_id)
    finally:
        conn.close()


def get_kb_article_by_id(article_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single KB article by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM knowledge_base WHERE id = ?;", (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_kb_articles(
    approved_only: bool = False,
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves all KB articles with optional filters."""
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM knowledge_base WHERE 1=1"
        params: List[Any] = []

        if approved_only:
            query += " AND is_approved = 1"
        if category:
            query += " AND category = ?"
            params.append(category)
        if search_query:
            query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
            term = f"%{search_query}%"
            params.extend([term, term, term])

        query += " ORDER BY id DESC;"
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def update_kb_article(
    article_id: int,
    title: str,
    category: str,
    content: str,
    tags: str,
    is_approved: int,
    db_path: Optional[str] = None,
) -> bool:
    """Updates an existing KB article."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE knowledge_base
                SET title = ?, category = ?, content = ?, tags = ?, is_approved = ?
                WHERE id = ?;
                """,
                (title, category, content, tags, is_approved, article_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_kb_article(article_id: int, db_path: Optional[str] = None) -> bool:
    """Deletes an article from the knowledge base."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM knowledge_base WHERE id = ?;", (article_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


# ============================================================================
# Drafts CRUD
# ============================================================================

def insert_draft(draft_data: Dict[str, Any], db_path: Optional[str] = None) -> int:
    """Inserts a newly generated response draft."""
    conn = get_connection(db_path)
    try:
        now = datetime.now().isoformat()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO drafts (email_id, draft_body, kb_article_ids, status, approved_by, sent_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    draft_data["email_id"],
                    draft_data["draft_body"],
                    draft_data.get("kb_article_ids", ""),
                    draft_data.get("status", "PENDING_APPROVAL"),
                    draft_data.get("approved_by", None),
                    draft_data.get("sent_at", None),
                    now,
                    now,
                ),
            )
            draft_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO activity_logs (email_id, draft_id, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    draft_data["email_id"],
                    draft_id,
                    "DRAFT_GENERATED",
                    f"Generated response draft (Status: {draft_data.get('status', 'PENDING_APPROVAL')})",
                    now,
                ),
            )
        return int(draft_id)
    finally:
        conn.close()


def get_draft_by_id(draft_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single draft by ID with associated email details."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT d.*, e.sender, e.subject, e.category, e.urgency, e.team, e.risk_flag
            FROM drafts d
            JOIN emails e ON d.email_id = e.id
            WHERE d.id = ?;
            """,
            (draft_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_drafts_by_email_id(email_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all drafts created for a specific email."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM drafts WHERE email_id = ? ORDER BY id DESC;",
            (email_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_all_drafts(status: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all drafts with joined email details, optionally filtered by status."""
    conn = get_connection(db_path)
    try:
        query = """
            SELECT d.*, e.sender, e.subject, e.category, e.urgency, e.team, e.risk_flag
            FROM drafts d
            JOIN emails e ON d.email_id = e.id
            WHERE 1=1
        """
        params: List[Any] = []
        if status:
            query += " AND d.status = ?"
            params.append(status)
        query += " ORDER BY d.id DESC;"

        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def update_draft_body(draft_id: int, new_body: str, db_path: Optional[str] = None) -> bool:
    """Updates draft text and resets approval status back to PENDING_APPROVAL."""
    conn = get_connection(db_path)
    try:
        now = datetime.now().isoformat()
        with conn:
            cursor = conn.execute(
                """
                UPDATE drafts
                SET draft_body = ?, status = 'PENDING_APPROVAL', approved_by = NULL, updated_at = ?
                WHERE id = ?;
                """,
                (new_body, now, draft_id),
            )
            updated = cursor.rowcount > 0
            if updated:
                conn.execute(
                    """
                    INSERT INTO activity_logs (draft_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?);
                    """,
                    (draft_id, "DRAFT_EDITED", "Draft updated by user; approval status reset to PENDING_APPROVAL", now),
                )
            return updated
    finally:
        conn.close()


def update_draft_status(
    draft_id: int,
    status: str,
    approved_by: Optional[str] = None,
    sent_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Updates the status of a draft."""
    conn = get_connection(db_path)
    try:
        now = datetime.now().isoformat()
        with conn:
            cursor = conn.execute(
                """
                UPDATE drafts
                SET status = ?, approved_by = ?, sent_at = ?, updated_at = ?
                WHERE id = ?;
                """,
                (status, approved_by, sent_at, now, draft_id),
            )
            updated = cursor.rowcount > 0
            if updated:
                conn.execute(
                    """
                    INSERT INTO activity_logs (draft_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?);
                    """,
                    (draft_id, f"DRAFT_{status}", f"Draft status set to {status} by {approved_by or 'System'}", now),
                )
            return updated
    finally:
        conn.close()


# ============================================================================
# Activity Logs & Summary Statistics
# ============================================================================

def log_activity(
    action: str,
    email_id: Optional[int] = None,
    draft_id: Optional[int] = None,
    details: str = "",
    db_path: Optional[str] = None,
) -> int:
    """Appends an event to the activity audit log."""
    conn = get_connection(db_path)
    try:
        now = datetime.now().isoformat()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO activity_logs (email_id, draft_id, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?);
                """,
                (email_id, draft_id, action, details, now),
            )
            return int(cursor.lastrowid)
    finally:
        conn.close()


def get_activity_logs(
    email_id: Optional[int] = None,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves recent audit log events."""
    conn = get_connection(db_path)
    try:
        if email_id:
            cursor = conn.execute(
                "SELECT * FROM activity_logs WHERE email_id = ? ORDER BY id DESC LIMIT ?;",
                (email_id, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?;",
                (limit,),
            )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_summary_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Computes summary counts for dashboards and reports."""
    conn = get_connection(db_path)
    try:
        total_emails = conn.execute("SELECT COUNT(*) FROM emails;").fetchone()[0]
        pending_drafts = conn.execute("SELECT COUNT(*) FROM drafts WHERE status = 'PENDING_APPROVAL';").fetchone()[0]
        approved_drafts = conn.execute("SELECT COUNT(*) FROM drafts WHERE status = 'APPROVED';").fetchone()[0]
        sent_drafts = conn.execute("SELECT COUNT(*) FROM drafts WHERE status = 'SENT';").fetchone()[0]
        high_risk_emails = conn.execute("SELECT COUNT(*) FROM emails WHERE risk_flag = 1;").fetchone()[0]
        critical_emails = conn.execute("SELECT COUNT(*) FROM emails WHERE urgency = 'Critical';").fetchone()[0]
        kb_articles_count = conn.execute("SELECT COUNT(*) FROM knowledge_base WHERE is_approved = 1;").fetchone()[0]

        return {
            "total_emails": total_emails,
            "pending_drafts": pending_drafts,
            "approved_drafts": approved_drafts,
            "sent_drafts": sent_drafts,
            "high_risk_emails": high_risk_emails,
            "critical_emails": critical_emails,
            "kb_articles_count": kb_articles_count,
        }
    finally:
        conn.close()
