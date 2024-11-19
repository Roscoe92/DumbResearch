import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re
from collections import defaultdict
import streamlit as st
from urllib.parse import urlparse
import os



def is_downloadable(urls):
    """
    Check if the URL points to a downloadable file by inspecting its headers or file extension.
    """
    try:
        # Add common file extensions for downloadable files
        downloadable_urls = []
        for url in urls:
            if url.lower().endswith(('.pdf', '.docx', '.xlsx', '.zip', '.csv', '.jpg', '.png', '.mp4')):
                downloadable_urls.append(url)
    except Exception as e:
        print(f"Error checking {url}: {e}")
    return downloadable_urls

def download_files(urls, save_dir):
    """
    Use Selenium WebDriver to download a file from a URL and save it to the specified directory.
    """
    chrome_driver_path = ""
    # Setup Chrome WebDriver with download preferences
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": save_dir,  # Set the directory where files will be downloaded
        "download.prompt_for_download": False,   # Suppress download prompt
        "safebrowsing.enabled": True             # Allow downloads even if Chrome flags them as "unsafe"
    }
    options.add_experimental_option("prefs", prefs)

    # Initialize WebDriver
    driver = webdriver.Chrome(service = Service(chrome_driver_path), options=options)
    for url in urls:
        try:
            # Navigate to the URL
            driver.get(url)
            time.sleep(5)  # Allow time for the file download to start

            # Wait until the file appears in the directory (Optional: add custom waiting logic)
            print(f"File from {url} should be downloaded to {save_dir}")
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
        finally:
            driver.quit()
