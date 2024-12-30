import subprocess
import shutil
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

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

def get_webdriver_options(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument('--ignore-certificate-errors')
    return options

def get_webdriver_service():
    service = Service(executable_path=get_chromedriver_path())
    return service

def run_selenium(domain, headless=False):
    """
    Attempts to fetch the HTML content of `domain` using Selenium.
    If headless=True, runs in headless mode; otherwise, opens a visible browser window.
    """
    html_content = None
    options = get_webdriver_options(headless=headless)
    service = get_webdriver_service()

    with webdriver.Chrome(options=options, service=service) as driver:
        try:
            driver.get(domain)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            html_content = driver.page_source
        except Exception as e:
            print(f"Error occurred while fetching {domain} in headless={headless} mode: {e}")

    return html_content
