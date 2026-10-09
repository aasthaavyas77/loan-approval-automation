"""
Loan application pre-screening (To-Be process automation).

Applies the business rules from the requirements (BR-01 to BR-05) to a batch of
SIMULATED loan applications and writes a summary report (FR-08).

All data is synthetic. All time and cost figures are stated assumptions.
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).parent
OUT = BASE / "output"


def load_config(path=BASE / "config.json"):
    """Read thresholds from a file so rules can change without editing code."""
    with open(path) as f:
        return json.load(f)


def generate_applications(n=1000, seed=42):
    """Create n fake loan applications."""
    rng = np.random.default_rng(seed)

    income = rng.lognormal(mean=11.2, sigma=0.4, size=n).round(-2)  # monthly, Rs
    loan_amount = (rng.uniform(50_000, 600_000, size=n)).round(-3)
    tenure = rng.choice([12, 24, 36, 48, 60], size=n)
    emi = (loan_amount / tenure * 1.15).round(0)  # simple EMI, 15% interest load

    score = rng.normal(720, 65, size=n).clip(300, 900).round(0)
    score = pd.Series(score)
    score[rng.random(n) < 0.03] = np.nan  # score unavailable for ~3%

    df = pd.DataFrame({
        "application_id": [f"APP{i:04d}" for i in range(1, n + 1)],
        "monthly_income": income,
        "proposed_emi": emi,
        "credit_score": score,
        "pan": rng.random(n) > 0.04,
        "aadhaar": rng.random(n) > 0.04,
        "salary_slip": rng.random(n) > 0.05,
    })

    kyc_passed = rng.random(n) > 0.10
    df["kyc_passed"] = kyc_passed
    df["kyc_retries_used"] = np.where(kyc_passed, 0, rng.choice([0, 1, 2, 2], size=n))

    # Hidden "would this customer default?" flag, used only by sensitivity.py.
    # Lower score and higher EMI burden -> higher chance of default.
    ratio = emi / income
    z = -(score.fillna(650) - 640) / 30 + (ratio - 0.2) * 5 - 0.3
    df["would_default"] = rng.random(n) < 1 / (1 + np.exp(-z))
    return df


def decide(row, cfg):
    """Return (decision, rule_id, reason) for one application."""
    # BR-01: required documents must be present
    missing = [d for d in cfg["required_documents"] if not row[d]]
    if missing:
        return "RETURNED", "BR-01", f"Missing documents: {', '.join(missing)}"

    # BR-04 (KYC part): failed KYC -> retry up to the limit, then reject
    if not row["kyc_passed"]:
        if row["kyc_retries_used"] >= cfg["max_kyc_retries"]:
            return "AUTO_REJECT", "BR-04", "KYC failed after maximum retries"
        return "RETURNED", "BR-04", "KYC mismatch - customer asked to correct details"

    # BR-05: no credit score -> manual review
    if pd.isna(row["credit_score"]):
        return "MANUAL_REVIEW", "BR-05", "Credit score unavailable"

    score = row["credit_score"]
    ratio = row["proposed_emi"] / row["monthly_income"]  # FR-04

    # BR-04 (credit part): clearly unsuitable -> reject
    if score < cfg["reject"]["min_score"] or ratio > cfg["reject"]["max_emi_ratio"]:
        return "AUTO_REJECT", "BR-04", f"Score {score:.0f} / EMI ratio {ratio:.0%} outside limits"

    # BR-02: clearly suitable -> approve
    if score >= cfg["auto_approve"]["min_score"] and ratio <= cfg["auto_approve"]["max_emi_ratio"]:
        return "AUTO_APPROVE", "BR-02", "Meets auto-approve criteria"

    # BR-03: everything in between -> human review
    return "MANUAL_REVIEW", "BR-03", f"Borderline: score {score:.0f}, EMI ratio {ratio:.0%}"


def run_screening(df, cfg):
    """Apply decide() to every application."""
    result = df.copy()
    result["emi_ratio"] = (result["proposed_emi"] / result["monthly_income"]).round(3)
    decisions = result.apply(lambda r: decide(r, cfg), axis=1, result_type="expand")
    result[["decision", "rule", "reason"]] = decisions
    # NFR-01 audit trail: application ID + rule ID + reason + timestamp per decision
    result["decided_at"] = datetime.now().isoformat(timespec="seconds")
    return result


def build_summary(result, cfg):
    """Counts, percentages, and estimated time saved (FR-08)."""
    n = len(result)
    counts = result["decision"].value_counts()
    get = lambda k: int(counts.get(k, 0))
    a = cfg["assumptions"]

    manual_hours = n * a["manual_minutes_per_application"] / 60
    new_hours = (get("MANUAL_REVIEW") * a["review_minutes"] + get("RETURNED") * a["followup_minutes"]) / 60
    auto_decided = get("AUTO_APPROVE") + get("AUTO_REJECT")

    return {
        "applications": n,
        "auto_approved": get("AUTO_APPROVE"),
        "manual_review": get("MANUAL_REVIEW"),
        "auto_rejected": get("AUTO_REJECT"),
        "returned_to_customer": get("RETURNED"),
        "auto_decided_pct": round(100 * auto_decided / n, 1),
        "manual_review_pct": round(100 * get("MANUAL_REVIEW") / n, 1),
        "baseline_manual_hours": round(manual_hours, 1),
        "new_manual_hours": round(new_hours, 1),
        "estimated_hours_saved": round(manual_hours - new_hours, 1),
    }


def save_chart(result, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = ["AUTO_APPROVE", "MANUAL_REVIEW", "AUTO_REJECT", "RETURNED"]
    counts = result["decision"].value_counts().reindex(order, fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(counts.index, counts.values, color=["#3B6D11", "#185FA5", "#A32D2D", "#888780"])
    for i, v in enumerate(counts.values):
        ax.text(i, v + 5, str(v), ha="center")
    ax.set_ylabel("Applications")
    ax.set_title("Screening outcome (1,000 simulated applications)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    cfg = load_config()
    OUT.mkdir(exist_ok=True)

    df = generate_applications(n=1000, seed=42)
    result = run_screening(df, cfg)
    summary = build_summary(result, cfg)

    result.drop(columns=["would_default"]).to_csv(OUT / "decisions.csv", index=False)
    pd.Series(summary).to_csv(OUT / "summary.csv", header=["value"])
    save_chart(result, OUT / "outcomes.png")

    print("=== Screening summary (simulated data) ===")
    for k, v in summary.items():
        print(f"{k:>24}: {v}")


if __name__ == "__main__":
    main()
