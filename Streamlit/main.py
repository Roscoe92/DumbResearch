import streamlit as st
from API.scraper import parse

import pandas as pd

st.title("Scraper")

domain = st.text_input("Enter a website URL:")

if st.button('Parse website'):
    result = parse(domain)
    st.write(result)
