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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

def get_driver():
    # Set Chrome options
    options = Options()
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    return driver

def get_all_links(domain):
    links_to_visit = []

    # # Ensure ChromeDriver is installed and up to date
    # chromedriver_autoinstaller.install()

    driver = get_driver()

    try:
        driver.get(domain)
        print('page loaded')
        html = driver.page_source
        time.sleep(10)

        soup = BeautifulSoup(html, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            # Resolve relative URLs
            full_url = urljoin(domain, a_tag['href'])
            links_to_visit.append(full_url)


    except Exception as e:
        print(f"Error visiting {full_url}: {e}")

    return links_to_visit

def extract_second_level_headlines(links):
    # Parse URLs and extract paths
    headlines = set()  # Use a set to avoid duplicates
    for link in links:
        parsed = urlparse(link)
        path_parts = parsed.path.strip('/').split('/')

        # Match second-level paths (e.g., /solutions/, /locations/)
        headline = "/".join(path_parts[:1])
        headlines.add(headline)

    return sorted(headlines)

def scrape_website(website):
    print('Launching Chrome browser')
    # Ensure ChromeDriver is installed and up to date
    # chromedriver_autoinstaller.install()

    chrome_driver_path = ""
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service = Service(chrome_driver_path), options = options)

    try:
        driver.get(website)
        print('page loaded')
        html = driver.page_source
        time.sleep(10)

        return html

    finally:
        driver.quit()

def extract_body_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""

def clean_body_content(body_content):
    soup = BeautifulSoup(body_content,'html.parser')

    for script_or_style in soup(['script', 'style']):
        script_or_style.extract()

    cleaned_content = soup.get_text(separator='\n')
    cleaned_content = '\n'.join(
        line.strip() for line in cleaned_content.splitlines() if line.strip()
        )
    return cleaned_content

def split_dom_content(dom_content, max_length = 6000):
    return [
        dom_content[i : i + max_length] for i in range(0,len(dom_content), max_length)
    ]

def is_valid_url(url):
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])  # Checks for scheme (http/https) and netloc (domain)

def re_match_second_level_headlines(headline, domain, links_to_visit):
    matching_urls = []
    headline_url = urljoin(domain, headline)
    matching_urls.extend([url for url in links_to_visit if url.startswith(headline_url)])
    return matching_urls

def get_select_data(headlines, domain):
    domain = domain
    subpage_links = set(get_all_links(domain))  # Assuming this fetches all sub-links from the domain

    # Dictionary to store concatenated text for each key
    content_dict = defaultdict(str)

    # Fetch and process links
    urls = {}
    for page in headlines:
        # Match URLs for the current page
        urls[page] = re_match_second_level_headlines(page, domain, subpage_links)
        for url in urls[page]:  # Iterate over the URLs for the current page
            if not is_valid_url(url):  # Validate URL before scraping
                print(f"Invalid URL skipped: {url}")
                continue

            print(f"Scraping URL: {url}")
            result = scrape_website(url)  # Scrape website content
            body_content = extract_body_content(result)  # Extract body content
            cleaned_content = clean_body_content(body_content)  # Clean the content

            # Concatenate the cleaned content to the respective key in the dictionary
            content_dict[page] += cleaned_content + " "  # Add a space between concatenated content

    return content_dict

# Function to extract deeper-level headlines
def extract_headlines_with_depth(links, depth):
    headlines = set()
    for link in links:
        parsed = urlparse(link)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) == depth:
            headline = "/".join(path_parts[:depth])
            headlines.add(headline)
    return sorted(headlines)
