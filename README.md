Loan application pre-screening (process automation)
Automates the rule-based screening step of a redesigned loan approval process and produces a summary report. This is the code part of a process improvement case study (as-is mapping, to-be design, requirements, business rules, traceability). Full write-up: <YOUR-NOTION-LINK>

All data is simulated. All time figures are assumptions.

What it does
Generates 1,000 fake loan applications
Applies business rules BR-01 to BR-05 in a fixed order (see below)
Logs every decision with application ID, rule ID, reason and timestamp (NFR-01)
Writes a summary report with counts and estimated manual effort (FR-08)
sensitivity.py tests different auto-approve score cut-offs and shows the trade-off
Rules (thresholds are in config.json)
Rules run in this order and the first match decides the outcome:

Order	Rule	Logic	Outcome
1	BR-01	PAN, Aadhaar or salary slip missing	Returned to customer
2	BR-04 (KYC)	KYC failed	Returned if retries are left; rejected after 2 retries
3	BR-05	Credit score unavailable	Manual review, whatever the EMI ratio
4	BR-04 (credit)	Score < 650, or EMI/income > 50%	Auto-reject with a reason
5	BR-02	Score >= 750 and EMI/income <= 40%	Auto-approve
6	BR-03	Everything else (score 650-749, or EMI/income 40-50%)	Manual review
Results (1,000 simulated applications, seed 42)
Metric	Target	Result
Auto-decided (approved + rejected)	~65%	43.8% (target not met)
Auto-approved	n/a	23.7%
Auto-rejected	n/a	20.1%
Sent to manual review	n/a	40.0%
Returned to customer	n/a	16.2%
Estimated manual effort	n/a	783 h to 147 h (-81%)
![Screening outcomes](output/outcomes.png)

Why 43.8% and not 65%
Approve cut-off	Auto-decided	Manual review	Default rate among approved	Risky approvals
700	63.1%	207	1.6%	7
725	53.4%	304	0.9%	3
750 (current)	43.8%	400	0.8%	2
775	35.6%	482	0.6%	1
Lowering the cut-off to 700 gets close to the 65% target but raises the default rate among approved customers. Across 20 random seeds, 700 averaged about 62% auto-decided with a 2.2% default rate, against about 43% and 0.8% at 750. The right cut-off is a risk-team decision, so 750 is kept as the baseline.

![Cut-off trade-off](output/sensitivity.png)

Run it
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 loan_screening.py # decisions + summary in ./output
python3 sensitivity.py # cut-off trade-off table + chart
python3 -m pytest -v # 11 unit tests

Files
loan_screening.py main script
config.json thresholds and time assumptions
sensitivity.py cut-off analysis
test_rules.py boundary, precedence and audit-trail tests
output/ decisions.csv, summary.csv, outcomes.png, sensitivity.csv, sensitivity.png
What the script covers
Requirement	In the script?
FR-01 online form with required uploads	Not built. BR-01 re-checks documents as a safeguard
FR-02 automatic data capture	Not built (the script reads structured data)
FR-03 KYC check	Partly: retry and reject logic on a simulated KYC result
FR-04 EMI/income ratio	Yes
FR-05 automatic routing	Yes
FR-06 status notifications	Not built
FR-07 rejection reason	Reason is recorded; sending it is not built
FR-08 summary report	Yes
NFR-01 audit trail	Yes (application ID, rule ID, reason, timestamp)
Limitations
Data and thresholds are simulated; real credit policy needs validation with a risk team.
The default flag is generated from the same score and EMI ratio the rules use, so the cut-off trade-off is built into the simulation. The risky-approval counts are small.
Returned applications are costed as a 5-minute follow-up only. If they come back and go to review at the same 40% rate, the estimated saving is about 78-79% instead of 81%.
Turnaround in days is not modelled; estimated manual effort is the proxy.
Duplicate-application handling and downtime queueing are designed but not built.
Credit bureau and KYC integration are assumed, not built.
Simplified EMI calculation (flat 15% interest load).
