"""Knowledge Base Retrieval Service.

Performs TF-IDF and keyword similarity matching against approved articles
in the SQLite database to find the most relevant troubleshooting guidance.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.database import (
    get_all_kb_articles,
    get_kb_article_by_id,
    insert_kb_article,
    update_kb_article,
    delete_kb_article,
)


def find_relevant_articles(
    query_text: str,
    category: Optional[str] = None,
    top_k: int = 3,
    min_similarity: float = 0.12,
    approved_only: bool = True,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves top-k most relevant knowledge base articles for a customer query.

    CRITICAL RULE: By default, ONLY approved articles (is_approved=1) are returned.

    Args:
        query_text: Combined subject and body text of the customer email.
        category: Optional category filter.
        top_k: Maximum number of articles to return.
        min_similarity: Minimum cosine similarity score required.
        approved_only: Enforce retrieving only approved articles.
        db_path: Optional database file path.

    Returns:
        List of matching articles with 'relevance_score' attached, sorted descending.
    """
    clean_query = query_text.strip()
    if not clean_query:
        return []

    # Fetch candidate articles from database
    candidates = get_all_kb_articles(approved_only=approved_only, category=category, db_path=db_path)
    if not candidates and category:
        # If no articles found under specific category, broaden to all categories
        candidates = get_all_kb_articles(approved_only=approved_only, category=None, db_path=db_path)

    if not candidates:
        return []

    # Prepare corpus for TF-IDF vectorization: combine title, tags, and content
    documents = []
    for art in candidates:
        doc = f"{art.get('title', '')} {art.get('tags', '')} {art.get('content', '')}"
        documents.append(doc)

    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform(documents)
        query_vec = vectorizer.transform([clean_query])

        similarities = cosine_similarity(query_vec, tfidf_matrix)[0]

        scored_articles: List[Dict[str, Any]] = []
        for idx, score in enumerate(similarities):
            # Keyword bonus: boost score if title terms match query
            art = dict(candidates[idx])
            title_terms = set(re.findall(r"\w+", art.get("title", "").lower()))
            query_terms = set(re.findall(r"\w+", clean_query.lower()))
            overlap = len(title_terms.intersection(query_terms))

            effective_score = float(score) + (overlap * 0.05)
            effective_score = min(1.0, effective_score)

            if effective_score >= min_similarity:
                art["relevance_score"] = round(effective_score, 3)
                scored_articles.append(art)

        # Sort by relevance score descending
        scored_articles.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_articles[:top_k]

    except Exception as e:
        print(f"Error computing KB similarity: {e}")
        return []
