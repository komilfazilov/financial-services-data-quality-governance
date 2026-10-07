-- =========================================================
-- Financial Services Data Quality & Governance Framework
-- SQL Validation Layer
--
-- All data used in this project is synthetic and created
-- solely for portfolio and educational purposes.
-- =========================================================


-- ---------------------------------------------------------
-- Load source and reporting datasets
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW source_data AS
SELECT *
FROM read_csv_auto(
    'data/raw/source_financial_data.csv',
    header = true
);


CREATE OR REPLACE VIEW reporting_data AS
SELECT *
FROM read_csv_auto(
    'data/raw/reporting_financial_data.csv',
    header = true
);


-- ---------------------------------------------------------
-- Create unique reporting population for reconciliation
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW reporting_unique AS
SELECT *
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY record_id
            ORDER BY record_id
        ) AS row_num
    FROM reporting_data
)
WHERE row_num = 1;


-- ---------------------------------------------------------
-- Data Quality Rule Results
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW dq_rule_results AS

-- 1. Completeness
SELECT
    'Missing Customer ID' AS rule,
    'Completeness' AS dimension,
    COUNT(*) AS failed_records
FROM reporting_data
WHERE customer_id IS NULL

UNION ALL

-- 2. Validity - Currency
SELECT
    'Invalid Currency',
    'Validity',
    COUNT(*)
FROM reporting_data
WHERE currency NOT IN (
    'USD',
    'EUR',
    'GBP',
    'CAD',
    'JPY'
)

UNION ALL

-- 3. Validity - Negative Amount
SELECT
    'Negative Position Amount',
    'Validity',
    COUNT(*)
FROM reporting_data
WHERE position_amount < 0

UNION ALL

-- 4. Consistency - Date Relationship
SELECT
    'Maturity Before Origination',
    'Consistency',
    COUNT(*)
FROM reporting_data
WHERE maturity_date IS NOT NULL
  AND maturity_date < origination_date

UNION ALL

-- 5. Validity - Product Type
SELECT
    'Invalid Product Type',
    'Validity',
    COUNT(*)
FROM reporting_data
WHERE product_type NOT IN (
    'Loans',
    'Deposits',
    'Commitments',
    'Securities'
)

UNION ALL

-- 6. Timeliness
SELECT
    'Stale As-Of Date',
    'Timeliness',
    COUNT(*)
FROM reporting_data
WHERE as_of_date <> (
    SELECT MAX(as_of_date)
    FROM source_data
)

UNION ALL

-- 7. Uniqueness
SELECT
    'Duplicate Record ID',
    'Uniqueness',
    COUNT(*) - COUNT(DISTINCT record_id)
FROM reporting_data

UNION ALL

-- 8. Accuracy / Reconciliation
SELECT
    'Source-to-Report Amount Mismatch',
    'Accuracy',
    COUNT(*)
FROM source_data s
INNER JOIN reporting_unique r
    ON s.record_id = r.record_id
WHERE ABS(
    s.position_amount - r.position_amount
) > 0.01;


-- ---------------------------------------------------------
-- Final SQL Data Quality Summary
-- ---------------------------------------------------------

SELECT
    rule,
    dimension,
    failed_records,

    ROUND(
        failed_records * 100.0 /
        (SELECT COUNT(*) FROM reporting_data),
        2
    ) AS failure_rate_pct

FROM dq_rule_results

ORDER BY failed_records DESC;