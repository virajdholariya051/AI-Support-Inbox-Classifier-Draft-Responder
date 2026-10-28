"""Unit tests for Risk Detector (backend/risk_detector.py)."""

from backend.risk_detector import detect_risk


def test_no_risk_normal_message():
    """Verifies that ordinary questions produce no risk flags."""
    res = detect_risk("How to update password?", "Could you please explain how I can change my password?")
    assert res["risk_flag"] == 0
    assert res["risk_score"] < 40
    assert len(res["risk_types"]) == 0


def test_churn_risk_detection():
    """Verifies detection of cancellation and switching to competitor."""
    res = detect_risk("Cancelling our service", "We are going to cancel subscription and take our business elsewhere.")
    assert res["risk_flag"] == 1
    assert "Customer Churn Risk" in res["risk_types"]
    assert res["risk_score"] >= 40


def test_legal_risk_detection():
    """Verifies detection of legal action and GDPR violation threats."""
    res = detect_risk("Legal notice", "Our attorney has advised us to file a lawsuit and report this GDPR violation.")
    assert res["risk_flag"] == 1
    assert "Legal / Compliance Risk" in res["risk_types"]
    assert res["severity"] in ["High", "Critical"]


def test_reputation_escalation_risk():
    """Verifies detection of social media blasting and manager escalation."""
    res = detect_risk("Unacceptable behavior", "This is completely unacceptable! I want to speak to your manager or I am taking this to Twitter.")
    assert "Severe Escalation / Reputation Risk" in res["risk_types"]
    assert len(res["reasons"]) >= 1


def test_combined_multi_risk():
    """Verifies that combined threats accumulate higher risk scores."""
    res = detect_risk("Lawsuit and Cancellation", "I demand full refund, we are cancelling our account, and our lawyer will contact you.")
    assert res["risk_flag"] == 1
    assert len(res["risk_types"]) >= 2
    assert res["severity"] == "Critical"
