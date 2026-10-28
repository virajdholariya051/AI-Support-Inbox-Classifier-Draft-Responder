"""Unit tests for Support Team Assignment (backend/team_assignment.py)."""

from backend.team_assignment import assign_support_team, TEAMS


def test_teams_list():
    """Verifies defined operational support teams."""
    assert len(TEAMS) >= 5
    assert "Tier 1 Support" in TEAMS
    assert "Tier 2 / Tech Support" in TEAMS
    assert "Billing Team" in TEAMS
    assert "Accounts & Security" in TEAMS
    assert "Product Management" in TEAMS


def test_technical_support_routing():
    """Verifies that technical issues route to Tier 2."""
    res = assign_support_team("Technical Support", urgency="High")
    assert res["team"] == "Tier 2 / Tech Support"
    assert res["sla_hours"] <= 4


def test_billing_routing():
    """Verifies that billing issues route to Billing Team."""
    res = assign_support_team("Billing & Payments", urgency="Medium")
    assert res["team"] == "Billing Team"
    assert res["sla_hours"] <= 16


def test_account_access_routing():
    """Verifies that credential and login issues route to Accounts & Security."""
    res = assign_support_team("Account Access", urgency="High")
    assert res["team"] == "Accounts & Security"
    assert res["sla_hours"] <= 4


def test_feature_request_routing():
    """Verifies that feature requests route to Product Management."""
    res = assign_support_team("Feature Request", urgency="Low")
    assert res["team"] == "Product Management"
    assert res["sla_hours"] == 48


def test_general_inquiry_routing():
    """Verifies that general inquiries route to Tier 1."""
    res = assign_support_team("General Inquiry", urgency="Low")
    assert res["team"] == "Tier 1 Support"
    assert res["sla_hours"] == 24


def test_high_risk_escalation_override():
    """Verifies that high risk with elevated urgency escalates to Executive Escalations."""
    res = assign_support_team("Billing & Payments", urgency="High", risk_flag=1)
    assert res["team"] == "Executive Escalations"
    assert res["sla_hours"] == 1
