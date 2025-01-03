import streamlit as st
from scraper.link_utils import get_all_links, process_link, preprocess, extract_topics

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
            links, _ = get_all_links(check_site)
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

# Run the app
if __name__ == "__main__":
    main()
