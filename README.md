# Loan application pre-screening (process automation)

Automates the rule-based part of a loan approval process (To-Be design) and
produces a summary report. **All data is simulated; all time figures are assumptions.**

## What it does
- Generates 1,000 fake loan applications
- Applies business rules BR-01 to BR-05 (documents, KYC, credit score, EMI/income ratio)
- Outputs a decision and reason for every application, plus a summary report
- `sensitivity.py` tests different auto-approve score cut-offs and shows the trade-off

## Rules (see `config.json` to change thresholds)
| Rule | Logic | Outcome |
|---|---|---|
| BR-01 | Missing PAN / Aadhaar / salary slip | Returned to customer |
| BR-02 | Score >= 750 and EMI/income <= 40% | Auto-approve |
| BR-03 | Anything in between | Manual review |
| BR-04 | Score < 650, or EMI/income > 50%, or KYC failed after 2 retries | Auto-reject (KYC mismatch with retries left: returned) |
| BR-05 | Credit score unavailable | Manual review |

## Run it
```bash
python3 -m venv venv && source venv/bin/activate
pip install pandas numpy matplotlib pytest
python3 loan_screening.py     # decisions + summary in ./output
python3 sensitivity.py        # cut-off trade-off table + chart
python3 -m pytest -v          # 7 unit tests for the rules
```

## Files
- `loan_screening.py` main script
- `config.json` thresholds and time assumptions
- `sensitivity.py` cut-off analysis
- `test_rules.py` boundary tests (e.g. 749 vs 750)
- `output/` decisions.csv, summary.csv, outcomes.png, sensitivity.csv, sensitivity.png

## Limitations
Synthetic data, simplified EMI calculation, no real credit bureau or KYC integration.
