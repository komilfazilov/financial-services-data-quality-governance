from pathlib import Path
import os

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SQL_FILE = (
    PROJECT_ROOT
    / "sql"
    / "data_quality_checks.sql"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sql_dq_summary.csv"
)


# Make project root the working directory so
# SQL relative paths resolve correctly.
os.chdir(PROJECT_ROOT)


with open(
    SQL_FILE,
    "r",
    encoding="utf-8"
) as file:
    sql_script = file.read()


connection = duckdb.connect()

result_df = connection.execute(
    sql_script
).fetchdf()


result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\nSQL DATA QUALITY VALIDATION RESULTS")
print("=" * 70)
print(result_df.to_string(index=False))

print(
    f"\nResults saved to: "
    f"{OUTPUT_FILE}"
)

connection.close()