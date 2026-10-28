"""Unit tests for Email Classifier & Urgency Detector."""

import pytest
from backend.email_classifier import classify_support_email, CATEGORIES
from backend.urgency_detector import detect_urgency


def test_classifier_categories():
    """Verifies that all standard categories are defined."""
    assert len(CATEGORIES) == 5
    assert "Technical Support" in CATEGORIES
    assert "Billing & Payments" in CATEGORIES
    assert "Account Access" in CATEGORIES
    assert "Feature Request" in CATEGORIES
    assert "General Inquiry" in CATEGORIES


def test_classify_technical_support():
    """Verifies classification of bug and crash reports."""
    res = classify_support_email("Application crashing", "Whenever I launch the app, it crashes with error code 500.")
    assert res["category"] == "Technical Support"
    assert res["confidence"] > 0.4
    assert "Technical Support" in res["probabilities"]


def test_classify_billing():
    """Verifies classification of invoice and refund inquiries."""
    res = classify_support_email("Invoice request", "Please send me my monthly VAT receipt and subscription invoice.")
    assert res["category"] == "Billing & Payments"
    assert res["confidence"] > 0.4


def test_classify_account_access():
    """Verifies classification of login, password, and 2FA issues."""
    res = classify_support_email("Cannot login", "I forgot my password and my 2FA authentication code is not working.")
    assert res["category"] == "Account Access"
    assert res["confidence"] > 0.4


def test_classify_feature_request():
    """Verifies classification of feature suggestions."""
    res = classify_support_email("Feature suggestion", "Would love to see Dark Mode and Slack integration added to your platform.")
    assert res["category"] == "Feature Request"
    assert res["confidence"] > 0.4


def test_classify_general_inquiry():
    """Verifies classification of general questions."""
    res = classify_support_email("Support hours", "What are your business operating hours and phone contact numbers?")
    assert res["category"] == "General Inquiry"
    assert res["confidence"] > 0.4


def test_classify_empty_input():
    """Verifies handling of empty inputs."""
    res = classify_support_email("", "")
    assert res["category"] in CATEGORIES
    assert "probabilities" in res


def test_urgency_critical():
    """Verifies detection of critical urgency signals like server outages."""
    res = detect_urgency("URGENT: Entire system outage", "Production server down! All users are blocked and service is unavailable.")
    assert res["urgency"] == "Critical"
    assert res["score"] >= 80
    assert any("outage" in r.lower() or "down" in r.lower() for r in res["reasons"])


def test_urgency_high():
    """Verifies detection of high urgency with ASAP and deadline phrasing."""
    res = detect_urgency("Need help ASAP", "We have an urgent deadline today and our export is failing right away.")
    assert res["urgency"] in ["High", "Critical"]
    assert res["score"] >= 50


def test_urgency_medium():
    """Verifies detection of medium urgency for regular issues."""
    res = detect_urgency("Issue with page loading", "The page is a bit slow and there is a glitch on the dashboard.")
    assert res["urgency"] in ["Medium", "High"]


def test_urgency_low():
    """Verifies detection of low urgency for general suggestions."""
    res = detect_urgency("Minor question regarding roadmap", "Just wondering if you have plans to add this when possible. Thank you!")
    assert res["urgency"] == "Low"
    assert res["score"] < 40


def test_urgency_caps_and_exclamations():
    """Verifies that ALL CAPS and multiple exclamation marks boost score."""
    res_normal = detect_urgency("System issue", "The report is not downloading.")
    res_stressed = detect_urgency("HELP ME NOW!!!", "THE SYSTEM IS COMPLETELY BROKEN AND NOT WORKING AT ALL!!!")
    assert res_stressed["score"] > res_normal["score"]
