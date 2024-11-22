import streamlit as st
import sys
import os
import subprocess
import shutil
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from API.scraper import parse


import pandas as pd

st.title("Scraper")

def get_chromium_version() -> str:
    try:
        result = subprocess.run(['chromium', '--version'], capture_output=True, text=True)
        version = result.stdout.split()[1]
        return version
    except Exception as e:
        return str(e)

def get_chromedriver_version() -> str:
    try:
        result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True)
        version = result.stdout.split()[1]
        return version
    except Exception as e:
        return str(e)

def get_chromedriver_path() -> str:
    return shutil.which('chromedriver')

def get_webdriver_options(proxy: str = None, socksStr: str = None) -> Options:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument('--ignore-certificate-errors')
    if proxy is not None and socksStr is not None:
        options.add_argument(f"--proxy-server={socksStr}://{proxy}")
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    return options

domain = st.text_input("Enter a website URL:")

def get_webdriver_service(logpath) -> Service:
    service = Service(
        executable_path=get_chromedriver_path(),
        log_output=logpath,
    )
    return service

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
