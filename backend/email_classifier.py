"""Email Classifier for AI Support Inbox.

Uses scikit-learn TF-IDF Vectorizer and Multinomial Naive Bayes trained on a curated
support email corpus, combined with rule-based heuristics for explainability and fallback.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

CATEGORIES = [
    "Technical Support",
    "Billing & Payments",
    "Account Access",
    "Feature Request",
    "General Inquiry",
]

# Curated academic training dataset covering core support categories
TRAINING_DATA: List[Tuple[str, str]] = [
    # Technical Support
    ("Application crash on launch", "Technical Support"),
    ("The mobile application keeps crashing when I open the settings page. Error code 500.", "Technical Support"),
    ("Getting 502 bad gateway and database timeout on endpoint /api/v1/orders", "Technical Support"),
    ("The system is frozen and unresponsive after the latest firmware upgrade", "Technical Support"),
    ("Bug report: screen goes blank when clicking the export to pdf button", "Technical Support"),
    ("API connection refused, SSL handshake failure on webhooks", "Technical Support"),
    ("Encountering unhandled null pointer exception in background worker", "Technical Support"),
    ("Latency is extremely high, requests take over 30 seconds to return data", "Technical Support"),
    ("Desktop client fails to sync local cache with the remote server", "Technical Support"),
    ("Javascript console error Uncaught TypeError: undefined is not a function", "Technical Support"),

    # Billing & Payments
    ("Where can I download my monthly tax invoice for March?", "Billing & Payments"),
    ("I was charged twice for the annual premium subscription plan", "Billing & Payments"),
    ("Requesting a full refund within the 14-day cancellation window", "Billing & Payments"),
    ("How do I update my credit card details and billing address?", "Billing & Payments"),
    ("Credit card transaction declined but bank shows pending deduction", "Billing & Payments"),
    ("Invoice shows incorrect sales tax calculation for our enterprise account", "Billing & Payments"),
    ("Please cancel my recurring monthly renewal before the next cycle", "Billing & Payments"),
    ("We need a receipt with our company VAT registration number", "Billing & Payments"),
    ("Pricing inquiry regarding enterprise tier volume discounts", "Billing & Payments"),
    ("Payment failed notification received even though card has funds", "Billing & Payments"),

    # Account Access
    ("Forgot my account password and the reset link has not arrived", "Account Access"),
    ("Lost my phone and cannot retrieve 2FA authentication code to sign in", "Account Access"),
    ("My account has been locked due to too many failed login attempts", "Account Access"),
    ("Need to change the primary email address registered to our account", "Account Access"),
    ("Unable to log in, getting invalid username or credentials error", "Account Access"),
    ("Two-factor authentication SMS OTP never reaches my mobile number", "Account Access"),
    ("How do I reset my security recovery questions?", "Account Access"),
    ("Employee departed from company, need to transfer account ownership", "Account Access"),
    ("Session keeps expiring immediately after logging in to the portal", "Account Access"),
    ("Unlock account request after temporary lockout period expired", "Account Access"),

    # Feature Request
    ("Could you please add support for Dark Mode in the web interface?", "Feature Request"),
    ("Feature suggestion: export analytics data directly to CSV and Excel", "Feature Request"),
    ("Would love to see an integration with Slack or Microsoft Teams", "Feature Request"),
    ("Please add keyboard shortcuts for quickly archiving inbox emails", "Feature Request"),
    ("Is there any plan to support multi-language localization in future releases?", "Feature Request"),
    ("Feature proposal: bulk editing of customer records from table view", "Feature Request"),
    ("It would be great to have customizable webhook trigger events", "Feature Request"),
    ("Requesting an automated auto-save draft functionality in the editor", "Feature Request"),
    ("Can you provide an option to change the default font size in dashboard?", "Feature Request"),
    ("Enhancement request: calendar view for upcoming scheduled tasks", "Feature Request"),

    # General Inquiry
    ("What are your customer support operating hours and phone contact?", "General Inquiry"),
    ("Where can I find your official documentation and developer guides?", "General Inquiry"),
    ("What is your service level agreement (SLA) for ticket response times?", "General Inquiry"),
    ("Are your services compliant with GDPR and ISO 27001 standards?", "General Inquiry"),
    ("Do you offer student or non-profit educational discounts?", "General Inquiry"),
    ("General question regarding server hosting locations and data centers", "General Inquiry"),
    ("Looking for information on your reseller and affiliate partnership program", "General Inquiry"),
    ("Can someone give us an overview of your platform capabilities?", "General Inquiry"),
    ("Where can I review your terms of service and privacy policies?", "General Inquiry"),
    ("Just checking if you support deployment on private cloud infrastructure", "General Inquiry"),
]

# Rule-based keyword mapping for backup/confidence boosting
KEYWORD_MAPPING: Dict[str, List[str]] = {
    "Technical Support": ["crash", "bug", "error", "exception", "freeze", "500", "502", "timeout", "broken", "stack trace", "glitch", "latency", "failed to sync"],
    "Billing & Payments": ["invoice", "receipt", "charge", "refund", "credit card", "billing", "payment", "subscription", "pricing", "vat", "renew", "cancel plan"],
    "Account Access": ["password", "login", "locked", "2fa", "otp", "authenticator", "credentials", "sign in", "reset", "unlock", "account access"],
    "Feature Request": ["feature", "suggestion", "roadmap", "enhancement", "dark mode", "add support", "would love", "proposal", "integration", "wishlist"],
    "General Inquiry": ["hours", "sla", "contact", "documentation", "inquiry", "partnership", "gdpr", "policy", "overview", "information", "hello"],
}


class EmailClassifier:
    """Classifies email text into support categories using TF-IDF + Naive Bayes."""

    def __init__(self) -> None:
        self.pipeline: Pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        lowercase=True,
                        stop_words="english",
                        sublinear_tf=True,
                    ),
                ),
                ("nb", MultinomialNB(alpha=0.1)),
            ]
        )
        self._train()

    def _train(self) -> None:
        """Trains the internal scikit-learn classifier pipeline on the training data."""
        texts = [item[0] for item in TRAINING_DATA]
        labels = [item[1] for item in TRAINING_DATA]
        self.pipeline.fit(texts, labels)

    def clean_text(self, text: str) -> str:
        """Sanitizes text by removing non-alphanumeric noise while preserving basic structure."""
        if not text:
            return ""
        # Keep basic punctuation for sentence structure, lowercase for processing
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned

    def classify_email(self, subject: str, body: str) -> Dict[str, Any]:
        """Classifies subject and body into a support category with confidence scores.
        
        Returns:
            Dict containing predicted category, confidence score (0-1), probability distribution,
            matched keywords, and classification method.
        """
        combined = f"{subject} {body}".strip()
        if not combined:
            return {
                "category": "General Inquiry",
                "confidence": 0.5,
                "probabilities": {cat: 0.2 for cat in CATEGORIES},
                "matched_keywords": [],
                "method": "Default (Empty Input)",
            }

        # 1. Scikit-learn Pipeline Prediction
        probs = self.pipeline.predict_proba([combined])[0]
        classes = list(self.pipeline.classes_)
        prob_dict = {cls_name: round(float(prob), 4) for cls_name, prob in zip(classes, probs)}

        # Predicted class from ML
        ml_best_class = classes[probs.argmax()]
        ml_confidence = float(probs.max())

        # 2. Keyword heuristic matching for explainability & edge cases
        lower_text = combined.lower()
        keyword_hits: Dict[str, List[str]] = {}
        for cat, keywords in KEYWORD_MAPPING.items():
            matched = [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", lower_text)]
            if matched:
                keyword_hits[cat] = matched

        # If keywords strongly suggest a category with high specificity, boost confidence
        final_category = ml_best_class
        final_confidence = ml_confidence
        matched_keywords = keyword_hits.get(ml_best_class, [])

        # Fallback heuristic: If ML confidence is low (< 0.45) but keyword match is prominent
        if ml_confidence < 0.45 and keyword_hits:
            best_cat = max(keyword_hits.keys(), key=lambda k: len(keyword_hits[k]))
            final_category = best_cat
            final_confidence = 0.70
            matched_keywords = keyword_hits[best_cat]

        return {
            "category": final_category,
            "confidence": round(final_confidence, 2),
            "probabilities": prob_dict,
            "matched_keywords": matched_keywords,
            "method": "Scikit-learn TF-IDF + Naive Bayes",
        }


# Global classifier instance
_classifier_instance: EmailClassifier | None = None


def get_email_classifier() -> EmailClassifier:
    """Returns a singleton instance of EmailClassifier."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = EmailClassifier()
    return _classifier_instance


def classify_support_email(subject: str, body: str) -> Dict[str, Any]:
    """Convenience helper to classify a support email."""
    classifier = get_email_classifier()
    return classifier.classify_email(subject, body)
