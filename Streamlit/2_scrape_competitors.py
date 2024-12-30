import streamlit as st
import pandas as pd
import io
import time
import re
import os
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from scraper.scraper import *
from scraper.link_utils import get_all_links, process_link, preprocess
from processing.extraction import scrape_to_df, run_chatgpt
from scraper.scraper import *


from openai import OpenAI

###########################################
# Scraping + GPT Code (your existing logic)
###########################################

# Paste or import all your previously defined functions here
# For brevity, I'm just showing placeholders and referencing them
# with the assumption that you have them in your codebase.

###########################################
# Streamlit Page 2: Scrape & Process
###########################################

def main():
    st.title("Scrape & Process Competitors")

    st.write("""
    This page takes the competitor websites from the first page
    and scrapes them to extract information based on your description.
    """)

    # 1) Verify if we have a competitor DataFrame from page 1
    if "competitor_df" not in st.session_state or st.session_state.competitor_df.empty:
        st.warning("No competitor data found in session state. Please go back to Page 1 and finalize your competitor list.")
        return

    # 2) Ask user for the description/instructions to GPT
    parse_description = st.text_area(
        "What columns or information do you want from these competitor websites?",
        help="Example: 'Please extract product names, features, target customers, and relevant KPIs.'"
    )

    # 3) Let user trigger the scraping process
    if st.button("Run Scraping & Extraction"):
        # Get all the websites from the session state DataFrame
        competitor_df = st.session_state.competitor_df
        # The relevant column is 'Website'
        websites = [w for w in competitor_df['Website'] if isinstance(w, str) and w.strip()]
        # Filter out duplicates or empty strings
        websites = list(set([w.strip() for w in websites if w.strip()]))

        if not websites:
            st.error("No valid websites to scrape.")
            return

        st.write(f"Scraping {len(websites)} websites...")

        # 4) Scrape each competitor's site (or pass them to your workflow).
        # We'll do a simplified version of your dumbresearch_workflow:
        start_time = time.time()
        # Preprocess returns a (link_library, content_dict)
        link_library, content_dict_master = preprocess(websites)

        # Then parse to DataFrame
        results = scrape_to_df(content_dict_master, parse_description)
        end_time = time.time()

        st.success(f"Scraping and extraction completed in {end_time - start_time:.2f} seconds.")

        # 5) Show results
        # 'results' is presumably a dict of {domain: DataFrame}
        st.write("### Extraction Results")
        st.write("Below are the DataFrames for each competitor domain.")

        # Store in session state so user can navigate or download
        st.session_state.scrape_results = results

        for domain, df in results.items():
            st.subheader(f"Data for {domain}")
            st.dataframe(df)

    # 6) If we have results, offer an Excel download
    if "scrape_results" in st.session_state and st.session_state.scrape_results:
        results = st.session_state.scrape_results
        if st.button("Download All Results as Excel"):
            # Build a multi-sheet Excel in memory
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                for domain, df in results.items():
                    sheet_name = domain.replace("http://", "").replace("https://", "")
                    # Sheet name must be <= 31 characters; slice if needed
                    sheet_name = sheet_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            excel_buffer.seek(0)

            st.download_button(
                label="Download XLSX",
                data=excel_buffer,
                file_name="competitor_scraping_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
