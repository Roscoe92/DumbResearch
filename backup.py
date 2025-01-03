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
    st.title("Scrape & Process Competitors (Page 2)")

    st.write("""
    This page takes the competitor websites from the first page
    and then:
    1. Lets you gather all subpages for each website.
    2. Lets you select which subpages to actually scrape.
    3. Preprocesses and runs the GPT extraction automatically.
    4. Displays the results and offers an Excel download.
    """)

    # 1) Verify if we have a competitor DataFrame from page 1
    if "competitor_df" not in st.session_state or st.session_state.competitor_df.empty:
        st.warning("No competitor data found in session state. Please go back to Page 1 and finalize your competitor list.")
        return

    # Convert the 'Website' column to a list of unique, cleaned domains
    competitor_df = st.session_state.competitor_df
    websites = [
        w.strip().lower().rstrip("/")
        for w in competitor_df["Website"]
        if isinstance(w, str) and w.strip()
    ]
    websites = list(set(websites))  # remove duplicates

    if not websites:
        st.error("No valid websites found in your competitor list.")
        return

    st.write("### 1) Gather Subpages for Each Competitor Website")

    # We'll store discovered subpages in session state as a dict: {domain: [list_of_subpages]}
    if "all_subpages_dict" not in st.session_state:
        st.session_state.all_subpages_dict = {}

    # Button to fetch subpages for each domain
    if st.button("Fetch Subpages"):
        # For each domain, get_all_links
        all_subpages_dict = {}
        for domain in websites:
            # Safely handle errors
            links, cleaned_content = get_all_links(domain)
            all_subpages_dict[domain] = links

        st.session_state.all_subpages_dict = all_subpages_dict
        st.success("Fetched all subpages for each domain.")

    # If subpages have been fetched, display them and let user select
    if st.session_state.all_subpages_dict:
        # Within your "if st.session_state.all_subpages_dict:" block:
        st.write("### 2) Select Which Subpages You Want to Scrape")
        st.write("Hint: Select pages that are high up in the hierachy, e.g. 'https://website/product' DumbResearch then loops through all its subpages")
        # We'll store the user's chosen subpages in another dict
        if "chosen_subpages" not in st.session_state:
            st.session_state.chosen_subpages = {}

        for domain, subpages_list in st.session_state.all_subpages_dict.items():
            st.write(f"**Domain**: {domain}")

            # Put all checkboxes inside an expander (so it collapses if there are many links)
            with st.expander(f"Subpages for {domain}", expanded=True):
                chosen_for_domain = []
                # Show each subpage as a checkbox
                for i, subpage in enumerate(subpages_list):
                    # You can default to True or False depending on what you want
                    # e.g. True if you want them all selected by default
                    checkbox_key = f"{domain}_{subpage}_{i}"

                    is_selected = st.checkbox(
                        subpage,
                        value=False,
                        key=checkbox_key
                    )
                    if is_selected:
                        chosen_for_domain.append(subpage)

                # Store the user's choice for this domain
                st.session_state.chosen_subpages[domain] = chosen_for_domain

    # 3) Button to run preprocess() on the chosen subpages
    if st.button("Run Preprocessing & Extraction"):
        if "chosen_subpages" not in st.session_state or not st.session_state.chosen_subpages:
            st.error("No subpages selected. Please fetch subpages and make a selection first.")
            return

        # Flatten the user's chosen subpages into a single list
        all_chosen_links = []
        for domain, subpages in st.session_state.chosen_subpages.items():
            all_chosen_links.extend(subpages)

        if not all_chosen_links:
            st.error("You haven't selected any links to scrape.")
            return

        st.write(f"Preprocessing {len(all_chosen_links)} subpages...")

        start_time = time.time()
        link_library, content_dict_master = preprocess(all_chosen_links)
        end_time = time.time()
        st.write(f"Finished preprocessing in {end_time - start_time:.2f} seconds.")

        # 4) Run scrape_to_df with an automated parse description (or none if your code can handle it)
        # We'll define a default parse description. Or you can remove it entirely if your code doesn't require it.
        default_parse_description = "Please extract any relevant textual information from the pages in a semicolon-delimited table."
        st.write("Running GPT extraction on the selected pages...")

        start_time = time.time()
        results = scrape_to_df(content_dict_master)
        end_time = time.time()
        st.success(f"Extraction completed in {end_time - start_time:.2f} seconds.")

        # Store results in session_state for display and download
        st.session_state.scrape_results = results

    # 5) Display results if available
    if "scrape_results" in st.session_state and st.session_state.scrape_results:
        results = st.session_state.scrape_results
        st.write("### Scraping & Extraction Results")

        for domain, df in results.items():
            st.subheader(f"Data for {domain}")
            st.dataframe(df)

        # 6) Button to download results as Excel
        if st.button("Download All Results as Excel"):
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                for domain, df in results.items():
                    sheet_name = domain.replace("http://", "").replace("https://", "")
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
