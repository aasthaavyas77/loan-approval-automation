"""Unit tests for the business rules. Run with: python3 -m pytest -v"""
import numpy as np
import pytest

from loan_screening import decide, generate_applications, load_config, run_screening

CFG = load_config()


def app(**overrides):
    """A clean application that passes everything; override fields per test."""
    base = {
        "monthly_income": 100_000, "proposed_emi": 30_000,  # ratio 0.30
        "credit_score": 780, "pan": True, "aadhaar": True, "salary_slip": True,
        "kyc_passed": True, "kyc_retries_used": 0,
    }
    base.update(overrides)
    return base


def test_clean_application_is_auto_approved():
    assert decide(app(), CFG)[0] == "AUTO_APPROVE"


def test_br02_score_boundary_750_approved_749_review():
    assert decide(app(credit_score=750), CFG)[0] == "AUTO_APPROVE"
    assert decide(app(credit_score=749), CFG)[0] == "MANUAL_REVIEW"


def test_br02_ratio_boundary_40_percent():
    assert decide(app(proposed_emi=40_000), CFG)[0] == "AUTO_APPROVE"  # exactly 0.40
    assert decide(app(proposed_emi=41_000), CFG)[0] == "MANUAL_REVIEW"  # 0.41


def test_br04_rejects_low_score_and_high_ratio():
    assert decide(app(credit_score=649), CFG)[0] == "AUTO_REJECT"
    assert decide(app(credit_score=650), CFG)[0] == "MANUAL_REVIEW"
    assert decide(app(proposed_emi=51_000), CFG)[0] == "AUTO_REJECT"  # 0.51
    assert decide(app(proposed_emi=50_000), CFG)[0] == "MANUAL_REVIEW"  # 0.50


def test_br01_missing_document_is_returned():
    decision, rule, reason = decide(app(salary_slip=False), CFG)
    assert (decision, rule) == ("RETURNED", "BR-01")
    assert "salary_slip" in reason


def test_br04_kyc_retry_then_reject():
    assert decide(app(kyc_passed=False, kyc_retries_used=1), CFG)[0] == "RETURNED"
    assert decide(app(kyc_passed=False, kyc_retries_used=2), CFG)[0] == "AUTO_REJECT"


def test_br05_missing_score_goes_to_review():
    assert decide(app(credit_score=np.nan), CFG)[0] == "MANUAL_REVIEW"


# --- Rule precedence: BR-01 -> BR-04 (KYC) -> BR-05 -> BR-04 (credit) -> BR-02 -> BR-03 ---

def test_precedence_missing_document_beats_failed_kyc():
    result = decide(app(salary_slip=False, kyc_passed=False, kyc_retries_used=2), CFG)
    assert result[:2] == ("RETURNED", "BR-01")


def test_precedence_failed_kyc_beats_missing_score():
    result = decide(app(kyc_passed=False, kyc_retries_used=2, credit_score=np.nan), CFG)
    assert result[:2] == ("AUTO_REJECT", "BR-04")


def test_precedence_missing_score_beats_high_emi_ratio():
    # EMI/income = 60% would normally reject, but no score -> manual review (BR-05)
    result = decide(app(credit_score=np.nan, proposed_emi=60_000), CFG)
    assert result[:2] == ("MANUAL_REVIEW", "BR-05")


# --- NFR-01 audit trail ---

def test_audit_trail_columns_present():
    result = run_screening(generate_applications(n=20, seed=1), CFG)
    for col in ["application_id", "rule", "reason", "decided_at"]:
        assert col in result.columns
    assert result["decided_at"].notna().all()
