import streamlit as st
import pandas as pd
import io
from datetime import date, datetime
from openai import OpenAI
from deutschland.bundesanzeiger import Bundesanzeiger
from processing.extraction import run_chatgpt
from Bundesanzeiger.bundesanzeiger import *

def main():
    st.title("Bundesanzeiger Research (Page 3)")

    st.write("""
    This page fetches and parses Bundesanzeiger reports for selected companies (by legal entity)
    from your previously created competitor DataFrame.
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

    # 2) Let user select which legal entities to fetch
    st.write("### 1) Select Legal Entities for Bundesanzeiger Lookup")
    selected_entities = st.multiselect(
        "Choose the companies (by legal entity) you want to fetch reports for:",
        options=legal_entities,
        default=legal_entities  # by default select them all
    )

    # Button to fetch reports
    if st.button("Fetch Bundesanzeiger Reports"):
        if not selected_entities:
            st.error("No legal entities selected.")
        else:
            # Filter competitor_df to only these entities
            chosen_companies_df = competitor_df[competitor_df["Legal entity"].isin(selected_entities)].copy()

            # 3) Run get_bundesanzeiger_reports
            st.write("Fetching Bundesanzeiger reports, please wait...")
            reports_dict = get_bundesanzeiger_reports(chosen_companies_df)

            # Store the raw dictionary in session_state
            st.session_state.ba_reports = reports_dict
            st.success(f"Fetched reports for {len(reports_dict)} selected entities.")
            st.write(reports_dict)
    # If we have ba_reports, parse them
    if "ba_reports" in st.session_state and st.session_state.ba_reports:
        st.write("### 2) Parse the Bundesanzeiger Reports")

        if st.button("Parse Reports"):
            ba_raw = st.session_state.ba_reports  # a dict {company_name: <list of reports>}

            # The get_bundesanzeiger_reports structure is {company_name: [report_dicts]}
            # But parse_bundesanzeiger_reports expects a dictionary keyed by a unique ID with fields like 'report', 'date', 'company'
            # So we need to transform it
            combined_reports = {}
            unique_id_counter = 0

            for company_name, reports_list in ba_raw.items():
                for rpt in reports_list:
                    # Each 'rpt' might look like:
                    # { "date": <datetime>, "report": <text>, "company": <str>, ... }
                    # We need a unique ID
                    unique_id = f"{company_name}_{unique_id_counter}"
                    combined_reports[unique_id] = reports_list[rpt]
                    unique_id_counter += 1

            # 4) parse the combined dictionary
            st.write("Parsing the fetched reports, please wait...")
            st.write(combined_reports)
            parsed_results = parse_bundesanzeiger_reports(combined_reports)

            # Store the final nested structure in session_state
            st.session_state.ba_parsed = parsed_results
            st.success("Parsed Bundesanzeiger reports successfully!")

    # 5) If we have parsed data, display & allow Excel download
    if "ba_parsed" in st.session_state and st.session_state.ba_parsed:
        st.write("### 3) View & Download Parsed Bundesanzeiger Data")
        ba_parsed = st.session_state.ba_parsed

        # Example display: we’ll loop through each company -> year -> report_id
        for company_name, years_dict in ba_parsed.items():
            st.subheader(f"**{company_name}**")
            for year, reports_dict in years_dict.items():
                st.write(f"**Year:** {year}")
                for report_id, data_dict in reports_dict.items():
                    st.write(f"**Report ID:** {report_id}")
                    # data_dict has e.g. "Income Statement", "KPIs", "Qualitative"
                    for table_name, df in data_dict.items():
                        st.write(f"**{table_name}**")
                        st.dataframe(df)

        # Let user download each company's data in one multi-sheet Excel
        if st.button("Download as Excel"):
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                # Flatten the nested structure into a set of sheets
                for company_name, years_dict in ba_parsed.items():
                    for year, rpt_dict in years_dict.items():
                        for report_id, tbl_dict in rpt_dict.items():
                            for table_name, df in tbl_dict.items():
                                # Construct sheet name
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
