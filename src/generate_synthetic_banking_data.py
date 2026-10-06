from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SEED = 42
NUMBER_OF_RECORDS = 10_000
AS_OF_DATE = pd.Timestamp("2026-10-01")

rng = np.random.default_rng(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Generate synthetic financial-services records
# ---------------------------------------------------------

product_types = rng.choice(
    ["Loans", "Deposits", "Commitments", "Securities"],
    size=NUMBER_OF_RECORDS,
    p=[0.35, 0.30, 0.15, 0.20],
)

subtype_map = {
    "Loans": ["Term Loan", "Revolving Loan"],
    "Deposits": ["Demand Deposit", "Term Deposit"],
    "Commitments": ["Credit Line", "Standby Commitment"],
    "Securities": ["Corporate Bond", "Treasury Note"],
}

product_subtypes = [
    rng.choice(subtype_map[product])
    for product in product_types
]

record_ids = [
    f"FS-{i:06d}"
    for i in range(1, NUMBER_OF_RECORDS + 1)
]

customer_ids = [
    f"CUST-{value:05d}"
    for value in rng.integers(1, 2501, NUMBER_OF_RECORDS)
]

customer_segments = rng.choice(
    ["Consumer", "Small Business", "Commercial", "Institutional"],
    size=NUMBER_OF_RECORDS,
    p=[0.25, 0.20, 0.35, 0.20],
)

currencies = rng.choice(
    ["USD", "EUR", "GBP", "CAD", "JPY"],
    size=NUMBER_OF_RECORDS,
    p=[0.70, 0.10, 0.08, 0.07, 0.05],
)

position_amounts = np.round(
    rng.lognormal(
        mean=10.5,
        sigma=1.0,
        size=NUMBER_OF_RECORDS,
    ),
    2,
)

start_date = pd.Timestamp("2018-01-01")

origination_dates = start_date + pd.to_timedelta(
    rng.integers(
        0,
        (AS_OF_DATE - start_date).days,
        NUMBER_OF_RECORDS,
    ),
    unit="D",
)

maturity_dates = origination_dates + pd.to_timedelta(
    rng.integers(
        30,
        3650,
        NUMBER_OF_RECORDS,
    ),
    unit="D",
)

# Convert to a writable pandas Series
maturity_dates = pd.Series(maturity_dates).copy()

# Demand deposits generally do not require a maturity date
demand_deposit_mask = np.array(product_subtypes) == "Demand Deposit"
maturity_dates.loc[demand_deposit_mask] = pd.NaT

statuses = rng.choice(
    ["Active", "Closed", "Pending"],
    size=NUMBER_OF_RECORDS,
    p=[0.78, 0.17, 0.05],
)

source_systems = rng.choice(
    [
        "CoreBank-A",
        "LendingHub",
        "DepositPlatform",
        "InvestmentPlatform",
    ],
    size=NUMBER_OF_RECORDS,
)

source_df = pd.DataFrame(
    {
        "record_id": record_ids,
        "customer_id": customer_ids,
        "product_type": product_types,
        "product_subtype": product_subtypes,
        "customer_segment": customer_segments,
        "currency": currencies,
        "position_amount": position_amounts,
        "origination_date": origination_dates,
        "maturity_date": maturity_dates,
        "status": statuses,
        "source_system": source_systems,
        "as_of_date": AS_OF_DATE,
    }
)

# Reporting data begins as an exact copy.
reporting_df = source_df.copy()

issue_truth = []


def record_issue(indices, issue_type):
    """Store known synthetic defects for later validation."""
    for index in indices:
        issue_truth.append(
            {
                "record_id": reporting_df.loc[index, "record_id"],
                "issue_type": issue_type,
            }
        )


# ---------------------------------------------------------
# Inject synthetic data-quality defects
# ---------------------------------------------------------

# 1. Missing customer IDs
indices = rng.choice(
    reporting_df.index,
    size=100,
    replace=False,
)
record_issue(indices, "MISSING_CUSTOMER_ID")
reporting_df.loc[indices, "customer_id"] = None


# 2. Invalid currency codes
indices = rng.choice(
    reporting_df.index,
    size=70,
    replace=False,
)
record_issue(indices, "INVALID_CURRENCY")
reporting_df.loc[indices, "currency"] = "XXX"


# 3. Negative position amounts
indices = rng.choice(
    reporting_df.index,
    size=70,
    replace=False,
)
record_issue(indices, "NEGATIVE_POSITION_AMOUNT")
reporting_df.loc[indices, "position_amount"] = (
    -reporting_df.loc[indices, "position_amount"].abs()
)


# 4. Maturity dates before origination dates
eligible = reporting_df[
    reporting_df["maturity_date"].notna()
].index

indices = rng.choice(
    eligible,
    size=80,
    replace=False,
)

record_issue(indices, "INVALID_MATURITY_DATE")

reporting_df.loc[indices, "maturity_date"] = (
    reporting_df.loc[indices, "origination_date"]
    - pd.to_timedelta(30, unit="D")
)


# 5. Invalid product types
indices = rng.choice(
    reporting_df.index,
    size=50,
    replace=False,
)
record_issue(indices, "INVALID_PRODUCT_TYPE")
reporting_df.loc[indices, "product_type"] = "UNKNOWN"


# 6. Stale reporting dates
indices = rng.choice(
    reporting_df.index,
    size=100,
    replace=False,
)
record_issue(indices, "STALE_AS_OF_DATE")

reporting_df.loc[indices, "as_of_date"] = (
    AS_OF_DATE - pd.to_timedelta(10, unit="D")
)


# 7. Source-to-report amount mismatches
indices = rng.choice(
    reporting_df.index,
    size=150,
    replace=False,
)
record_issue(indices, "SOURCE_REPORT_AMOUNT_MISMATCH")

reporting_df.loc[indices, "position_amount"] *= rng.uniform(
    0.90,
    1.10,
    size=len(indices),
)

reporting_df["position_amount"] = (
    reporting_df["position_amount"].round(2)
)


# 8. Duplicate reporting records
duplicate_indices = rng.choice(
    reporting_df.index,
    size=50,
    replace=False,
)

duplicate_rows = reporting_df.loc[
    duplicate_indices
].copy()

for record_id in duplicate_rows["record_id"]:
    issue_truth.append(
        {
            "record_id": record_id,
            "issue_type": "DUPLICATE_RECORD",
        }
    )

reporting_df = pd.concat(
    [reporting_df, duplicate_rows],
    ignore_index=True,
)


# ---------------------------------------------------------
# Save datasets
# ---------------------------------------------------------

source_df.to_csv(
    RAW_DATA_DIR / "source_financial_data.csv",
    index=False,
)

reporting_df.to_csv(
    RAW_DATA_DIR / "reporting_financial_data.csv",
    index=False,
)

pd.DataFrame(issue_truth).to_csv(
    PROCESSED_DATA_DIR / "injected_issue_truth.csv",
    index=False,
)


print("Synthetic financial-services data generated successfully.")
print(f"Source records: {len(source_df):,}")
print(f"Reporting records: {len(reporting_df):,}")
print(f"Injected issues: {len(issue_truth):,}")