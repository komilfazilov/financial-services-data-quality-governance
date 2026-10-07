from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


source_df = pd.read_csv(
    RAW_DATA_DIR / "source_financial_data.csv",
    parse_dates=[
        "origination_date",
        "maturity_date",
        "as_of_date",
    ],
)

reporting_df = pd.read_csv(
    RAW_DATA_DIR / "reporting_financial_data.csv",
    parse_dates=[
        "origination_date",
        "maturity_date",
        "as_of_date",
    ],
)


VALID_PRODUCTS = {
    "Loans",
    "Deposits",
    "Commitments",
    "Securities",
}

VALID_CURRENCIES = {
    "USD",
    "EUR",
    "GBP",
    "CAD",
    "JPY",
}


def test_source_record_count():
    assert len(source_df) == 10_000


def test_reporting_record_count():
    assert len(reporting_df) == 10_050


def test_missing_customer_ids_detected():
    assert reporting_df["customer_id"].isna().sum() == 100


def test_invalid_currency_detected():
    invalid_currency = ~reporting_df["currency"].isin(
        VALID_CURRENCIES
    )

    assert invalid_currency.sum() == 70


def test_negative_position_amounts_detected():
    negative_amount = (
        reporting_df["position_amount"] < 0
    )

    assert negative_amount.sum() == 70


def test_invalid_maturity_dates_detected():
    invalid_maturity = (
        reporting_df["maturity_date"].notna()
        &
        (
            reporting_df["maturity_date"]
            < reporting_df["origination_date"]
        )
    )

    assert invalid_maturity.sum() == 80


def test_invalid_product_types_detected():
    invalid_product = ~reporting_df[
        "product_type"
    ].isin(VALID_PRODUCTS)

    assert invalid_product.sum() == 50


def test_stale_as_of_dates_detected():
    expected_as_of_date = source_df[
        "as_of_date"
    ].max()

    stale_dates = (
        reporting_df["as_of_date"]
        != expected_as_of_date
    )

    assert stale_dates.sum() == 100


def test_duplicate_record_ids_detected():
    duplicates = reporting_df[
        "record_id"
    ].duplicated(
        keep="first"
    )

    assert duplicates.sum() == 50
def test_source_to_report_amount_mismatches_detected():
    reporting_unique = (
        reporting_df
        .drop_duplicates(
            subset="record_id",
            keep="first"
        )
    )

    reconciliation_df = source_df[
        ["record_id", "position_amount"]
    ].merge(
        reporting_unique[
            ["record_id", "position_amount"]
        ],
        on="record_id",
        suffixes=("_source", "_reporting"),
    )

    amount_difference = (
        reconciliation_df["position_amount_reporting"]
        - reconciliation_df["position_amount_source"]
    ).abs()

    mismatches = amount_difference > 0.01

    assert mismatches.sum() == 219
    