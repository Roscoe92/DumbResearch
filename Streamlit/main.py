import streamlit as st
import sys
import os
import subprocess
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import time
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

def get_webdriver_options():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument('--ignore-certificate-errors')
    return options

domain = st.text_input("Enter a website URL:")

def get_webdriver_service():
    service = Service(
        executable_path=get_chromedriver_path()
    )
    return service

def run_selenium(domain):
    name = None
    html_content = None
    options = get_webdriver_options()
    service = get_webdriver_service()
    with webdriver.Chrome(options=options, service=service) as driver:
        url = domain
        try:
            driver.get(url)
            time.sleep(2)
            # Wait for the element to be rendered:
            element = WebDriverWait(driver=driver, timeout=10).until(lambda x: x.find_elements(by=By.CSS_SELECTOR, value="h2.eventcard-content-name"))
            name = element[0].get_property('attributes')[0]['name']
            html_content = driver.page_source
        except Exception as e:
            st.error(body='Selenium Exception occured!', icon='🔥')
            st.error(body=str(e), icon='🔥')
        finally:
            performance_log = driver.get_log('performance')
            browser_log = driver.get_log('browser')
    return html_content

if st.button('Parse website'):
    # result = parse(domain)
    result = run_selenium(domain)
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
