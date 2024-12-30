import datetime
import pandas as pd
from processing.extraction import run_chatgpt
from processing.extraction import parse_semicolon_csv_to_dataframe

def parse_semicolon_csv_to_dataframe(csv_text):
    """
    Dynamically determine the max number of columns across all lines
    and use that to build the DataFrame.
    """
    lines = [line.strip() for line in csv_text.strip().splitlines() if line.strip()]
    if not lines:
        return pd.DataFrame()

    # Split everything first
    splitted_lines = [row.split(";") for row in lines]

    # Find the maximum column count
    max_cols = max(len(sl) for sl in splitted_lines)

    # First row is still used as headers, but it might not have all columns
    headers = splitted_lines[0]
    if len(headers) < max_cols:
        # Pad the header row with "ColumnX" or "empty" for missing columns
        missing_count = max_cols - len(headers)
        headers += [f"ExtraCol{i+1}" for i in range(missing_count)]
    elif len(headers) > max_cols:
        # If the header has more columns than any data row, just truncate it
        headers = headers[:max_cols]

    # For all subsequent rows, pad or truncate
    data_rows = []
    for row in splitted_lines[1:]:
        if len(row) < max_cols:
            row += ["empty"] * (max_cols - len(row))
        elif len(row) > max_cols:
            row = row[:max_cols]
        data_rows.append(row)

    df = pd.DataFrame(data_rows, columns=headers)
    return df


#############################################
# 2) Individual Extraction Functions
#############################################

def extract_income_statement(report_text):
    """
    Extracts the Income Statement from the given `report_text`.
    Returns a DataFrame, or empty DataFrame if none found.
    """
    # Single-task instructions to ChatGPT
    income_statement_instructions = """
    You are tasked with extracting only the Income Statement data
    from the following report. The output should be formatted as
    a semicolon-delimited table with a header row.

    Instructions:
    1. Only output the Income Statement (no other tables).
    2. Use semicolons (;) to separate columns.
    3. If certain cells are empty, write 'empty'.
    4. Do not include extra commentary or text outside the table.
    5. The first line should be the header row.

    Here is the input:
    {report_text}
    """

    prompt = income_statement_instructions.format(report_text=report_text)
    response_text = run_chatgpt(prompt)
    response_text = response_text.choices[0].message.content
    df = parse_semicolon_csv_to_dataframe(response_text)
    return df


def extract_operational_kpis(report_text):
    """
    Extracts important operational KPIs from the report text,
    such as production volume, customer count, churn rate, ARPU, etc.
    Returns a DataFrame.
    """
    kpi_instructions = """
    You are tasked with extracting only the operational KPIs from
    the following report. Examples of such KPIs include:
    - Number of customers or clients
    - Churn rate
    - ARPU (Average Revenue per User)
    - Employee headcount
    - Production volume
    - Utilization rates
    - Other similar quantitative metrics

    Output a semicolon-delimited table with a header row.
    Each row should contain:
       - KPI Name
       - KPI Value
       - (Optionally) a KPI Description

    Only output this single table, no other text.

    Here is the input:
    {report_text}
    """

    prompt = kpi_instructions.format(report_text=report_text)
    response_text = run_chatgpt(prompt)
    response_text = response_text.choices[0].message.content
    df = parse_semicolon_csv_to_dataframe(response_text)
    return df


def extract_qualitative_info(report_text):
    """
    Extracts only qualitative information, e.g.,
    management commentary, forward-looking statements, strategic objectives, etc.
    Returns a DataFrame with two columns: label, content.
    """
    qualitative_instructions = """
    You are tasked with extracting only qualitative information
    such as management commentary, forward-looking statements,
    strategic objectives, or other narrative insights from the
    following report. Each piece of qualitative info should be
    categorized under a 'label', with the actual commentary in 'content'.

    Output a semicolon-delimited table with this header:
    "label";"content"

    Only output this single table, no extra text or lines.

    Here is the input:
    {report_text}
    """

    prompt = qualitative_instructions.format(report_text=report_text)
    response_text = run_chatgpt(prompt)
    response_text = response_text.choices[0].message.content
    df = parse_semicolon_csv_to_dataframe(response_text)
    return df


#############################################
# 3) Orchestrator for a Single Report
#############################################

def parse_single_report(report_data):
    """
    Given one report (dictionary with keys like date, company, report),
    runs the three extraction functions and returns a dictionary of DataFrames.
    e.g. {
        "Income Statement": <DataFrame>,
        "KPIs": <DataFrame>,
        "Qualitative": <DataFrame>
    }
    """

    report_text = report_data.get("report", "")
    if not report_text:
        # Return empty placeholders if no text
        return {
            "Income Statement": pd.DataFrame(),
            "KPIs": pd.DataFrame(),
            "Qualitative": pd.DataFrame()
        }

    # Calls each extraction function separately
    income_df = extract_income_statement(report_text)
    kpi_df = extract_operational_kpis(report_text)
    qual_df = extract_qualitative_info(report_text)

    return {
        "Income Statement": income_df,
        "KPIs": kpi_df,
        "Qualitative": qual_df
    }


#############################################
# 4) parse_bundesanzeiger_reports
#############################################

def parse_bundesanzeiger_reports(reports_dict):
    """
    Takes a dictionary of reports, keyed by unique IDs, where each value
    is a dictionary containing 'date', 'company', 'report' text, etc.

    Returns a final structure:
    {
        <company_name>: {
            <year>: {
                <report_id>: {
                   "Income Statement": DataFrame,
                   "KPIs": DataFrame,
                   "Qualitative": DataFrame
                },
                ...
            },
            ...
        },
        ...
    }
    """

    master_outputs = {}

    for report_id, report_data in reports_dict.items():
        # Identify the company
        company_name = report_data.get("company", "Unknown Company")

        # Parse out the year from the date
        raw_date = report_data.get("date", None)
        parsed_year = None
        if isinstance(raw_date, datetime.date):
            parsed_year = raw_date.year
        elif isinstance(raw_date, str):
            try:
                dt = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
                parsed_year = dt.year
            except ValueError:
                print(f"Could not parse date for report {report_id}: {raw_date}")
        if not parsed_year:
            print(f"Skipping report {report_id}: No valid year.")
            continue

        # Build structure: master_outputs[company][year][report_id]
        if company_name not in master_outputs:
            master_outputs[company_name] = {}
        if parsed_year not in master_outputs[company_name]:
            master_outputs[company_name][parsed_year] = {}

        # Parse the single report using the orchestrator function
        results_for_this_report = parse_single_report(report_data)

        # Save the results
        master_outputs[company_name][parsed_year][report_id] = results_for_this_report

    return master_outputs
