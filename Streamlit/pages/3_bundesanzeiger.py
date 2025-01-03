import streamlit as st
import pandas as pd
import io
import os
from datetime import date, datetime
from openai import OpenAI
from deutschland.bundesanzeiger import Bundesanzeiger
from country_db.bundesanzeiger import *
from processing.extraction import run_chatgpt
from country_db.companies_house import get_company_filing_history, fetch_all_and_store  # Import your Companies House functions


os.environ["COMPANIES_HOUSE_API_KEY"] = "cd88de94-9a32-496c-8970-bdaa3ec3d61c"

def main():
    st.title("Company Filings Research (Page 3)")

    st.write("""
    This page fetches and parses company filings from Bundesanzeiger (Germany) or Companies House (UK)
    for selected companies based on their legal entity and country information.
    """)

    # 1) Ensure we have competitor_df in session_state
    if "competitor_df" not in st.session_state or st.session_state.competitor_df.empty:
        st.warning("No competitor data found in session state. Please go back to Page 1 and finalize your competitor list.")
        return

    competitor_df = st.session_state.competitor_df

    # Extract the unique legal entity names
    legal_entities = competitor_df["Legal entity"].dropna().unique().tolist()
    if not legal_entities:
        st.warning("No 'Legal entity' data found in competitor_df.")
        return

    st.write("### 1) Select Legal Entities for Lookup")
    selected_entities = st.multiselect(
        "Choose the companies (by legal entity) you want to fetch filings for:",
        options=legal_entities,
        default=legal_entities  # by default select them all
    )

    # Filter the DataFrame for selected entities
    chosen_companies_df = competitor_df[competitor_df["Legal entity"].isin(selected_entities)].copy()

    # Separate companies by country
    germany_companies = chosen_companies_df[chosen_companies_df["Country"].str.contains("Germany", na=False)]
    uk_companies = chosen_companies_df[
        chosen_companies_df["Country"].str.contains("UK|England|Wales|Scotland", case=False, na=False)
    ]

    # Fetch Bundesanzeiger Reports
    if st.button("Fetch Bundesanzeiger Reports (Germany)"):
        if germany_companies.empty:
            st.warning("No German companies selected.")
        else:
            st.write("Fetching Bundesanzeiger reports, please wait...")
            ba_reports = get_bundesanzeiger_reports(germany_companies)

            # Store the raw Bundesanzeiger data in session_state
            st.session_state.ba_reports = ba_reports
            st.success(f"Fetched Bundesanzeiger reports for {len(ba_reports)} German companies.")
            st.write(ba_reports)

    # Fetch Companies House Filings
    if st.button("Fetch Companies House Filings (UK)"):
        if uk_companies.empty:
            st.warning("No UK companies selected.")
        else:
            st.write("Fetching Companies House filings, please wait...")
            uk_filing_results = {}
            for _, row in uk_companies.iterrows():
                company_name = row["Legal entity"]
                try:
                    result = get_company_filing_history(company_name, os.getenv("COMPANIES_HOUSE_API_KEY"))
                    if "error" in result:
                        st.error(f"Error fetching filings for {company_name}: {result['error']}")
                    else:
                        uk_filing_results[company_name] = result
                except Exception as e:
                    st.error(f"Unexpected error for {company_name}: {e}")

            # Store the UK filings data in session_state
            st.session_state.uk_filings = uk_filing_results
            st.success(f"Fetched Companies House filings for {len(uk_filing_results)} UK companies.")
            st.write(uk_filing_results)

    with st.form("save_company_filings"):
        path = st.text_input("Enter a path where you'd like to save the company accounts, e.g. ''/Users/peterpan/Downloads':")
        submitted = st.form_submit_button("Save company accounts")

    if submitted:
        # Check if `uk_filings` is available
        if "uk_filings" not in st.session_state or not st.session_state.uk_filings:
            st.warning("Please fetch Companies House filings before attempting to save the reports.")
        elif not path.strip():
            st.warning("Please enter a valid path, where you'd like to save the reports.")
        else:
            # Retrieve the UK filings from session_state
            uk_filing_results = st.session_state.uk_filings
            for company,value in uk_filing_results.items():
                st.write(fetch_all_and_store(value, path))
            st.success(f"Saved reports for {len(uk_filing_results)} UK companies")

    # Parse Bundesanzeiger Reports
    if "ba_reports" in st.session_state and st.button("Parse Bundesanzeiger Reports"):
        ba_raw = st.session_state.ba_reports

        combined_reports = {}
        unique_id_counter = 0
        for company_name, reports_list in ba_raw.items():
            for rpt in reports_list:
                unique_id = f"{company_name}_{unique_id_counter}"
                combined_reports[unique_id] = rpt
                unique_id_counter += 1

        st.write("Parsing the fetched Bundesanzeiger reports, please wait...")
        parsed_results = parse_bundesanzeiger_reports(combined_reports)

        # Store parsed results
        st.session_state.ba_parsed = parsed_results
        st.success("Parsed Bundesanzeiger reports successfully!")

    # Download parsed Bundesanzeiger Reports
    if "ba_parsed" in st.session_state and st.button("Download Bundesanzeiger Reports as Excel"):
        ba_parsed = st.session_state.ba_parsed

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            for company_name, years_dict in ba_parsed.items():
                for year, reports_dict in years_dict.items():
                    for report_id, data_dict in reports_dict.items():
                        for table_name, df in data_dict.items():
                            sheet_name = f"{company_name[:10]}_{year}_{table_name[:10]}"
                            sheet_name = sheet_name[:31]  # Excel limit
                            df.to_excel(writer, sheet_name=sheet_name, index=False)

        excel_buffer.seek(0)
        st.download_button(
            label="Download Excel",
            data=excel_buffer,
            file_name="bundesanzeiger_reports.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
