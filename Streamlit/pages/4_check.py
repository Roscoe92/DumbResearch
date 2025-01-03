import streamlit as st
from scraper.link_utils import get_all_links, process_link, preprocess,extract_topics

def main():
    check_site = st.text_input(
            "Add any additional competitors by entering their websites (comma-separated):"
        )
    if st.button("Fetch Subpages"):
        links, _ = get_all_links(check_site)

    return st.write(links)

# Example usage
if __name__ == "__main__":
    main()
