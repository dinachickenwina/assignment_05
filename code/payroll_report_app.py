"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""

import streamlit as st

from payroll import (
    build_history,
    hours_grid,
    load_employees,
    load_export,
    missed_weeks,
    pay_by_month,
    summarize_employees,
)

st.title("Salt City Coffee — Quarterly Payroll Report")
st.caption(
    "Upload weekly payroll exports to review hours and pay by employee, "
    "department, and date."
)

employees = load_employees()
uploads = st.file_uploader(
    "Payroll exports",
    type="csv",
    accept_multiple_files=True,
    key="exports",
)

if uploads:
    history = build_history([load_export(upload) for upload in uploads], employees)
    unmatched = (
        history.loc[history["department"].isna(), "employeeid"]
        .dropna()
        .astype(str)
        .unique()
    )
    if len(unmatched):
        ids = ", ".join(unmatched)
        st.warning(
            f"Rows for employee ID(s) {ids} have no department and were left out of "
            "the reports."
        )

    report_history = history.dropna(subset=["department"])
    if report_history.empty:
        st.info("No uploaded rows match an employee on the roster.")
    else:
        departments = sorted(report_history["department"].unique())
        department = st.selectbox("Department", ["All", *departments], key="department")
        first_date = report_history["pay_date"].min().date()
        last_date = report_history["pay_date"].max().date()
        date_range = st.date_input(
            "Pay date range",
            value=(first_date, last_date),
            key="dates",
        )

        selected = report_history
        if department != "All":
            selected = selected[selected["department"] == department]

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            selected = selected[
                selected["pay_date"].dt.date.between(start_date, end_date)
            ]

        st.subheader(f"{department} payroll")
        metric_columns = st.columns(4)
        metric_columns[0].metric("Weeks", selected["week_ending"].nunique())
        metric_columns[1].metric("Employees", selected["employee_id"].nunique())
        metric_columns[2].metric(
            "Total hours", f"{selected['hours_worked'].sum():,.2f}"
        )
        metric_columns[3].metric(
            "Total gross pay", f"${selected['gross_pay'].sum():,.2f}"
        )

        monthly_pay = pay_by_month(selected)
        st.bar_chart(monthly_pay, x="month")
        st.dataframe(summarize_employees(selected), use_container_width=True)
        grid = hours_grid(selected)
        st.dataframe(grid, use_container_width=True)
        st.dataframe(missed_weeks(grid), use_container_width=True)
        st.download_button(
            "Download monthly payroll CSV",
            monthly_pay.to_csv(index=False),
            file_name="payroll_by_month.csv",
            mime="text/csv",
            key="download",
        )
