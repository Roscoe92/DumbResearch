import streamlit as st
import pandas as pd
import io
import time
import re
import os
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from scraper.scraper import *
from scraper.link_utils import get_all_links, process_link, preprocess,extract_topics
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

    # Store discovered subpages in session state as a dict: {domain: [list_of_subpages]}
    if "all_subpages_dict" not in st.session_state:
        st.session_state.all_subpages_dict = {}

    # Button to fetch subpages for each domain
    if st.button("Fetch Subpages"):
        all_subpages_dict = {}
        for domain in websites:
            # Fetch all links for each domain
            links, _ = get_all_links(domain)
            all_subpages_dict[domain] = links

        st.session_state.all_subpages_dict = all_subpages_dict
        st.success("Fetched all subpages for each domain.")

    # Process subpages with `extract_topics` if they exist
    if st.session_state.all_subpages_dict:
        st.write("### 2) Select Topics to Scrape")
        if "selected_topics" not in st.session_state:
            st.session_state.selected_topics = {}

        for domain, subpages_list in st.session_state.all_subpages_dict.items():
            st.write(f"**Domain**: {domain}")

            # Use `extract_topics` to get the links and topics
            topics_df = extract_topics(subpages_list, domain)
            st.write("**Available Topics**:")
            st.dataframe(topics_df)

            # Allow users to select topics
            selected_topics = st.multiselect(
                f"Select topics to scrape for {domain}",
                options=topics_df.index.tolist(),
                key=f"topics_{domain}"
            )
            st.session_state.selected_topics[domain] = selected_topics

        # Filter the DataFrame for selected topics
        filtered_links = []
        for domain, selected_topics in st.session_state.selected_topics.items():
            if selected_topics:
                topics_df = extract_topics(st.session_state.all_subpages_dict[domain], domain)
                domain_links = topics_df.loc[selected_topics]["links"].tolist()
                filtered_links.extend(domain_links)

        # 3) Run preprocess() on the filtered links
        if st.button("Run Preprocessing & Extraction"):
            if not filtered_links:
                st.error("No topics selected. Please select topics first.")
                return

            st.write(f"Preprocessing {len(filtered_links)} subpages...")

            start_time = time.time()
            link_library, content_dict_master = preprocess(filtered_links)
            end_time = time.time()
            st.write(f"Finished preprocessing in {end_time - start_time:.2f} seconds.")

            # 4) Run scrape_to_df with an automated parse description
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
                    # Sanitize sheet name
                    sheet_name = domain.replace("http://", "").replace("https://", "")
                    sheet_name = re.sub(r'[\\/*?:"<>|]', "", sheet_name)  # Remove invalid characters
                    sheet_name = sheet_name[:31]  # Truncate to maximum length
                    if not sheet_name:  # Fallback in case sheet_name becomes empty
                        sheet_name = "Sheet"

                    # Write to Excel
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
