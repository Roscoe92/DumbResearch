import streamlit as st
from API.scraper import parse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

st.title("Scraper")

domain = st.text_input("Enter a website URL:")

if st.button('Parse website'):
    result = parse(domain)
    st.write(result)

# Print the current Python path
st.write("Python path:", sys.path)

# Print the current working directory
st.write("Working directory:", os.getcwd())

# Attempt to manually import scrape_logic
try:
    import scrape_logic
    st.write("scrape_logic imported successfully")
except ImportError as e:
    st.write(f"ImportError: {e}")
