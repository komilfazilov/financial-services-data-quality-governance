from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Financial Services Data Quality Dashboard",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "source_financial_data.csv"
)

REPORTING_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "reporting_financial_data.csv"
)

DQ_SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sql_dq_summary.csv"
)

REMEDIATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "remediation_tracker.csv"
)


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

@st.cache_data
def load_data():

    source_df = pd.read_csv(
        SOURCE_FILE,
        parse_dates=[
            "origination_date",
            "maturity_date",
            "as_of_date",
        ],
    )

    reporting_df = pd.read_csv(
        REPORTING_FILE,
        parse_dates=[
            "origination_date",
            "maturity_date",
            "as_of_date",
        ],
    )

    dq_summary_df = pd.read_csv(
        DQ_SUMMARY_FILE
    )

    remediation_df = pd.read_csv(
        REMEDIATION_FILE,
        parse_dates=[
            "opened_date",
            "target_date",
        ],
    )
    remediation_df["opened_date"] = (
    remediation_df["opened_date"].dt.strftime("%Y-%m-%d")
)

    remediation_df["target_date"] = (
    remediation_df["target_date"].dt.strftime("%Y-%m-%d")
)
    return (
        source_df,
        reporting_df,
        dq_summary_df,
        remediation_df,
    )


(
    source_df,
    reporting_df,
    dq_summary_df,
    remediation_df,
) = load_data()


# ---------------------------------------------------------
# Data Quality dimension scores
# ---------------------------------------------------------

dimension_scores = (
    dq_summary_df
    .groupby("dimension")
    .agg(
        failed_records=("failed_records", "sum"),
        rules_evaluated=("rule", "count"),
    )
    .reset_index()
)

dimension_scores["records_evaluated"] = (
    dimension_scores["rules_evaluated"]
    * len(reporting_df)
)

dimension_scores.loc[
    dimension_scores["dimension"] == "Accuracy",
    "records_evaluated"
] = len(source_df)

dimension_scores["dq_score_pct"] = (
    100
    - (
        dimension_scores["failed_records"]
        / dimension_scores["records_evaluated"]
        * 100
    )
).round(2)


# ---------------------------------------------------------
# Overall KPIs
# ---------------------------------------------------------

total_rule_evaluations = int(
    dimension_scores[
        "records_evaluated"
    ].sum()
)

total_failed_checks = int(
    dimension_scores[
        "failed_records"
    ].sum()
)

overall_dq_score = round(
    (
        1
        - total_failed_checks
        / total_rule_evaluations
    )
    * 100,
    2,
)

highest_risk_dimension = (
    dimension_scores.loc[
        dimension_scores[
            "dq_score_pct"
        ].idxmin(),
        "dimension",
    ]
)


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.title(
    "Financial Services Data Quality & Governance Dashboard"
)

st.caption(
    "Interactive portfolio demonstration using entirely synthetic data."
)

st.info(
    "This project uses synthetic data created solely for "
    "educational and portfolio purposes. It contains no "
    "proprietary, confidential, production, or employer-owned data."
)


# ---------------------------------------------------------
# KPI row
# ---------------------------------------------------------

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Overall DQ Score",
    f"{overall_dq_score}%"
)

col2.metric(
    "Reporting Records",
    f"{len(reporting_df):,}"
)

col3.metric(
    "DQ Rules",
    len(dq_summary_df)
)

col4.metric(
    "Failed Evaluations",
    f"{total_failed_checks:,}"
)

col5.metric(
    "Highest-Risk Dimension",
    highest_risk_dimension
)


# ---------------------------------------------------------
# Dashboard tabs
# ---------------------------------------------------------

overview_tab, remediation_tab, data_tab = st.tabs(
    [
        "Data Quality Overview",
        "Remediation Tracker",
        "Data Explorer",
    ]
)


# =========================================================
# TAB 1 - DATA QUALITY OVERVIEW
# =========================================================

with overview_tab:

    st.subheader(
        "Data Quality Performance"
    )

    left_col, right_col = st.columns(2)

    with left_col:

        dimension_chart = px.bar(
            dimension_scores.sort_values(
                "dq_score_pct",
                ascending=True,
            ),
            x="dq_score_pct",
            y="dimension",
            orientation="h",
            title="Data Quality Score by Dimension",
            labels={
                "dq_score_pct":
                    "Data Quality Score (%)",
                "dimension":
                    "Data Quality Dimension",
            },
            text="dq_score_pct",
        )

        dimension_chart.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside",
        )

        dimension_chart.update_xaxes(
            range=[95, 100]
        )

        st.plotly_chart(
            dimension_chart,
            use_container_width=True,
        )

    with right_col:

        rule_chart = px.bar(
            dq_summary_df.sort_values(
                "failed_records",
                ascending=True,
            ),
            x="failed_records",
            y="rule",
            orientation="h",
            title="Detected Issues by Data Quality Rule",
            labels={
                "failed_records":
                    "Failed Records",
                "rule":
                    "Data Quality Rule",
            },
            hover_data=[
                "dimension",
                "failure_rate_pct",
            ],
        )

        st.plotly_chart(
            rule_chart,
            use_container_width=True,
        )


    st.subheader(
        "Data Quality Rule Results"
    )

    st.dataframe(
        dq_summary_df.sort_values(
            "failed_records",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )


    st.subheader(
        "Portfolio Composition"
    )

    product_distribution = (
        reporting_df[
            "product_type"
        ]
        .value_counts()
        .reset_index()
    )

    product_distribution.columns = [
        "product_type",
        "record_count",
    ]

    product_chart = px.bar(
        product_distribution,
        x="product_type",
        y="record_count",
        title="Reporting Records by Product Type",
        labels={
            "product_type":
                "Product Type",
            "record_count":
                "Number of Records",
        },
    )

    st.plotly_chart(
        product_chart,
        use_container_width=True,
    )


# =========================================================
# TAB 2 - REMEDIATION TRACKER
# =========================================================

with remediation_tab:

    st.subheader(
        "Data Quality Remediation Management"
    )

    severity_options = sorted(
        remediation_df[
            "severity"
        ].unique()
    )

    status_options = sorted(
        remediation_df[
            "status"
        ].unique()
    )

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:

        selected_severity = st.multiselect(
            "Severity",
            options=severity_options,
            default=severity_options,
        )

    with filter_col2:

        selected_status = st.multiselect(
            "Status",
            options=status_options,
            default=status_options,
        )


    filtered_remediation = remediation_df[
        remediation_df[
            "severity"
        ].isin(
            selected_severity
        )
        &
        remediation_df[
            "status"
        ].isin(
            selected_status
        )
    ]


    critical_count = (
        filtered_remediation[
            "severity"
        ]
        .eq("Critical")
        .sum()
    )

    overdue_count = (
        filtered_remediation[
            "target_status"
        ]
        .eq("Overdue")
        .sum()
    )

    rem_col1, rem_col2, rem_col3 = st.columns(3)

    rem_col1.metric(
        "Open Issues",
        len(filtered_remediation)
    )

    rem_col2.metric(
        "Critical Issues",
        int(critical_count)
    )

    rem_col3.metric(
        "Overdue Issues",
        int(overdue_count)
    )


    st.dataframe(
        filtered_remediation[
            [
                "issue_id",
                "rule",
                "dimension",
                "severity",
                "failed_records",
                "owner",
                "status",
                "opened_date",
                "target_date",
                "aging_days",
                "target_status",
                "remediation_action",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# TAB 3 - DATA EXPLORER
# =========================================================

with data_tab:

    st.subheader(
        "Synthetic Reporting Data Explorer"
    )
    st.caption(
    "The dataset intentionally contains synthetic data-quality defects, "
    "including invalid product classifications, for demonstration purposes."
)
    product_options = sorted(
        reporting_df[
            "product_type"
        ].dropna().unique()
    )

    selected_products = st.multiselect(
        "Product Type",
        options=product_options,
        default=product_options,
    )

    filtered_data = reporting_df[
        reporting_df[
            "product_type"
        ].isin(
            selected_products
        )
    ]

    st.write(
        f"Displaying "
        f"{len(filtered_data):,} records"
    )

    display_data = filtered_data.copy()

for column in [
    "origination_date",
    "maturity_date",
    "as_of_date",
]:
    display_data[column] = (
        display_data[column]
        .dt.strftime("%Y-%m-%d")
    )

st.dataframe(
    display_data,
    use_container_width=True,
    hide_index=True,
)
    