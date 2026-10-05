"""
Threshold sensitivity analysis.

Re-runs the screening with different auto-approve credit score cut-offs and
shows the trade-off: more auto-approvals vs. more risky approvals.

"Risky approval" = an auto-approved customer who (in the simulated data)
would later default. All data is synthetic and illustrative.
"""
import copy

import pandas as pd

from loan_screening import OUT, generate_applications, load_config, run_screening

CUTOFFS = [700, 725, 750, 775]


def main():
    base_cfg = load_config()
    df = generate_applications(n=1000, seed=42)
    rows = []

    for cutoff in CUTOFFS:
        cfg = copy.deepcopy(base_cfg)
        cfg["auto_approve"]["min_score"] = cutoff
        result = run_screening(df, cfg)

        approved = result[result["decision"] == "AUTO_APPROVE"]
        auto_decided = result["decision"].isin(["AUTO_APPROVE", "AUTO_REJECT"]).mean()
        rows.append({
            "approve_cutoff": cutoff,
            "auto_approved": len(approved),
            "auto_decided_pct": round(100 * auto_decided, 1),
            "manual_review": int((result["decision"] == "MANUAL_REVIEW").sum()),
            "default_rate_among_approved_pct": round(100 * approved["would_default"].mean(), 1),
            "risky_approvals": int(approved["would_default"].sum()),
        })

    table = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    table.to_csv(OUT / "sensitivity.csv", index=False)
    print(table.to_string(index=False))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.bar(table["approve_cutoff"].astype(str), table["auto_decided_pct"], color="#185FA5")
    ax1.set_xlabel("Auto-approve credit score cut-off")
    ax1.set_ylabel("Auto-decided (%)", color="#185FA5")
    ax2 = ax1.twinx()
    ax2.plot(table["approve_cutoff"].astype(str), table["default_rate_among_approved_pct"],
             color="#A32D2D", marker="o")
    ax2.set_ylabel("Default rate among approved (%)", color="#A32D2D")
    ax1.set_title("Cut-off trade-off (simulated data)")
    fig.tight_layout()
    fig.savefig(OUT / "sensitivity.png", dpi=150)


if __name__ == "__main__":
    main()
