from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sql_dq_summary.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "remediation_tracker.csv"
)

REPORT_DATE = pd.Timestamp("2026-10-07")


dq_summary = pd.read_csv(INPUT_FILE)


remediation_plan = {
    "Source-to-Report Amount Mismatch": {
        "severity": "Critical",
        "owner": "Data Reconciliation Team",
        "status": "In Progress",
        "opened_date": "2026-09-25",
        "remediation_action": (
            "Investigate source-to-report transformation logic, "
            "identify affected records, correct mapping or processing "
            "rules, and complete reconciliation."
        ),
    },
    "Missing Customer ID": {
        "severity": "High",
        "owner": "Customer Data Team",
        "status": "Open",
        "opened_date": "2026-09-28",
        "remediation_action": (
            "Identify upstream records missing customer identifiers, "
            "validate source population, and implement completeness controls."
        ),
    },
    "Stale As-Of Date": {
        "severity": "High",
        "owner": "Data Operations Team",
        "status": "In Progress",
        "opened_date": "2026-09-29",
        "remediation_action": (
            "Review batch timing and reporting-date logic, correct stale "
            "records, and implement timeliness monitoring."
        ),
    },
    "Maturity Before Origination": {
        "severity": "High",
        "owner": "Product Data Team",
        "status": "Open",
        "opened_date": "2026-10-01",
        "remediation_action": (
            "Validate date transformation rules and source values, correct "
            "invalid date relationships, and strengthen consistency controls."
        ),
    },
    "Invalid Currency": {
        "severity": "Medium",
        "owner": "Reference Data Team",
        "status": "Open",
        "opened_date": "2026-10-02",
        "remediation_action": (
            "Correct invalid currency values and enforce approved reference "
            "data values during ingestion."
        ),
    },
    "Negative Position Amount": {
        "severity": "Medium",
        "owner": "Financial Data Team",
        "status": "In Progress",
        "opened_date": "2026-10-02",
        "remediation_action": (
            "Review affected balances and transformation rules, validate "
            "sign conventions, and correct invalid amounts."
        ),
    },
    "Invalid Product Type": {
        "severity": "Medium",
        "owner": "Reference Data Team",
        "status": "Open",
        "opened_date": "2026-10-03",
        "remediation_action": (
            "Map invalid product values to approved classifications and "
            "introduce reference-data validation."
        ),
    },
    "Duplicate Record ID": {
        "severity": "Medium",
        "owner": "Data Engineering Team",
        "status": "Monitoring",
        "opened_date": "2026-10-03",
        "remediation_action": (
            "Identify duplicate-generation logic, correct upstream processing, "
            "and add uniqueness checks before publication."
        ),
    },
}


severity_sla_days = {
    "Critical": 7,
    "High": 14,
    "Medium": 30,
    "Low": 45,
}


tracker_rows = []

for index, row in dq_summary.iterrows():

    plan = remediation_plan[row["rule"]]

    opened_date = pd.Timestamp(plan["opened_date"])

    target_date = (
        opened_date
        + pd.Timedelta(
            days=severity_sla_days[plan["severity"]]
        )
    )

    aging_days = (
        REPORT_DATE - opened_date
    ).days

    days_to_target = (
        target_date - REPORT_DATE
    ).days

    if days_to_target < 0:
        target_status = "Overdue"
    elif days_to_target <= 5:
        target_status = "Due Soon"
    else:
        target_status = "On Track"

    tracker_rows.append(
        {
            "issue_id": f"DQ-{index + 1:03d}",
            "rule": row["rule"],
            "dimension": row["dimension"],
            "severity": plan["severity"],
            "failed_records": int(row["failed_records"]),
            "failure_rate_pct": row["failure_rate_pct"],
            "owner": plan["owner"],
            "status": plan["status"],
            "opened_date": opened_date.date(),
            "target_date": target_date.date(),
            "aging_days": aging_days,
            "target_status": target_status,
            "remediation_action": plan["remediation_action"],
        }
    )


remediation_df = pd.DataFrame(tracker_rows)


severity_order = {
    "Critical": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4,
}

remediation_df["severity_order"] = (
    remediation_df["severity"]
    .map(severity_order)
)

remediation_df = (
    remediation_df
    .sort_values(
        [
            "severity_order",
            "failed_records",
        ],
        ascending=[
            True,
            False,
        ],
    )
    .drop(
        columns="severity_order"
    )
)


remediation_df.to_csv(
    OUTPUT_FILE,
    index=False,
)


print("\nDATA QUALITY REMEDIATION TRACKER")
print("=" * 100)

print(
    remediation_df[
        [
            "issue_id",
            "rule",
            "severity",
            "failed_records",
            "owner",
            "status",
            "aging_days",
            "target_status",
        ]
    ].to_string(index=False)
)

print(
    f"\nRemediation tracker saved to: "
    f"{OUTPUT_FILE}"
)