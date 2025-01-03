import os
import streamlit as st
from scraper.link_utils import get_all_links, process_link, preprocess, extract_topics
from scraper.scraper import run_selenium

def main():
    # Initialize `links` in session state if not already set
    if "links" not in st.session_state:
        st.session_state["links"] = []

    # Input field for website
    check_site = st.text_input(
        "Add any additional competitors by entering their websites (comma-separated):"
    )

    # Button to fetch subpages
    if st.button("Fetch Subpages"):
        if check_site:  # Ensure `check_site` is not empty
            links, _ = run_selenium(check_site)
            st.session_state["links"] = links  # Update session state
            st.success("Subpages fetched successfully!")
        else:
            st.warning("Please enter a valid website.")

    # Display results if available
    if st.session_state["links"]:
        st.write("Fetched Links:")
        st.write(st.session_state["links"])
    else:
        st.write("No links fetched yet.")

    # Check for ChromeDriver log and provide download option
    if os.path.exists("chromedriver.log"):
        st.download_button(
            label="Download ChromeDriver Log",
            data=open("chromedriver.log", "rb"),
            file_name="chromedriver.log",
            mime="text/plain"
        )
    else:
        st.warning("ChromeDriver log file not found.")

# Run the app
if __name__ == "__main__":
    main()
