import streamlit as st
from scrape_logic.scrape import (
    scrape_website,
    split_dom_content,
    clean_body_content,
    extract_body_content,
    get_all_links,
    extract_second_level_headlines,
    re_match_second_level_headlines,
    get_select_data
)
from scrape_logic.parse import parse_with_ollama, parse_with_chatgpt
from download import is_downloadable, download_files
from scrape_logic.user_comms import introduction

import pandas as pd
import streamlit as st
from io import BytesIO

st.title("Scraper")
st.header(introduction)
domain = st.text_input("Enter a website URL:")

# Initialize session state for second-level headlines and selected pages
if "second_level_headlines" not in st.session_state:
    st.session_state.second_level_headlines = []

if "selected_pages" not in st.session_state:
    st.session_state.selected_pages = []


# Parse website to extract second-level headlines
if st.button("Parse website"):
    if domain:
        st.write("Parsing...")
        links = get_all_links(domain)  # Ensure this function returns a list of links
        st.session_state.second_level_headlines = extract_second_level_headlines(links)
        st.session_state.downloadable_files = is_downloadable(links)

# Display checkboxes for second-level headlines
if st.session_state.second_level_headlines:
    st.write("The website you passed has the following subdomains. Please select the ones you are interested in:")
    for headline in st.session_state.second_level_headlines:
        if st.checkbox(headline, key=f"checkbox_{headline}"):
            if headline not in st.session_state.selected_pages:
                st.session_state.selected_pages.append(headline)
        else:
            if headline in st.session_state.selected_pages:
                st.session_state.selected_pages.remove(headline)

if st.button("Scrape site"):
    if not st.session_state.selected_pages:
        st.warning("Please first parse the page and then select at least one subdomain to scrape.")
    else:
        st.write("Scraping...")
        result = get_select_data(st.session_state.selected_pages, domain)
        st.text_area("Scraped Data:", str(result), height=200)
        st.session_state.dom_content = result

if 'dom_content' in st.session_state and st.session_state.dom_content:
    for key in st.session_state.dom_content:
        parse_description = st.text_area(f'Please describe what you would like to do with the {key} scraped content. For the best output be specific on what you want the output to contain as rows and columns and provide relevant context for your ask, the model will default to providing tabular output so you can download it to excel')

        if st.button(f'Parse {key} with Ollama', key=f"ollama_button_{key}"):
            if parse_description:
                st.write('Parsing content')
                dom_chunks = split_dom_content(st.session_state.dom_content[key])
                result = parse_with_ollama(dom_chunks, parse_description)
                st.write(result)

                # Convert the result to a DataFrame if it’s in tabular format
                try:
                    # Assuming the result is formatted as a string table
                    table_data = pd.read_csv(BytesIO(result.encode()), sep="\t")  # Adjust separator if needed
                except Exception:
                    st.error("Could not parse the result as a table.")
                    table_data = None

                if table_data is not None:
                    # Display the DataFrame
                    st.dataframe(table_data)

                    # Allow download as Excel
                    excel_buffer = BytesIO()
                    table_data.to_excel(excel_buffer, index=False, engine='xlsxwriter')
                    excel_buffer.seek(0)

                    st.download_button(
                        label=f"Download {key} table as Excel",
                        data=excel_buffer,
                        file_name=f"{key}_table.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        if st.button(f'Parse {key} with ChatGPT'):
            if parse_description:
                st.write('Parsing content')
                dom_chunks = split_dom_content(st.session_state.dom_content[key])
                result = parse_with_chatgpt(dom_chunks, parse_description)
                st.write(result)

                # Convert the result to a DataFrame if it’s in tabular format
                try:
                    # Assuming the result is formatted as a string table
                    table_data = pd.read_csv(BytesIO(result.encode()), sep="\t")  # Adjust separator if needed
                except Exception:
                    st.error("Could not parse the result as a table.")
                    table_data = None

                if table_data is not None:
                    # Display the DataFrame
                    st.dataframe(table_data)

                    # Allow download as Excel
                    excel_buffer = BytesIO()
                    table_data.to_excel(excel_buffer, index=False, engine='xlsxwriter')
                    excel_buffer.seek(0)

                    st.download_button(
                        label=f"Download {key} table as Excel",
                        data=excel_buffer,
                        file_name=f"{key}_table.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
