import subprocess
import shutil
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

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
        options.add_argument("--headless")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")  # Required for environments with small /dev/shm
    options.add_argument("--disable-gpu")           # Avoid GPU issues
    # options.add_argument("--window-size=1920x1080") # Ensure sufficient resolution for rendering
    return options


def get_driver(options):
    return webdriver.Chrome(
        service=Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        ), options=options,)

def get_webdriver_service():
    service = Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        )
    return service


def run_selenium(domain, headless=False):
    """
    Attempts to fetch the HTML content of `domain` using Selenium.
    If headless=True, runs in headless mode; otherwise, opens a visible browser window.
    """
    html_content = None
    options = get_webdriver_options(headless=headless)
    driver = get_driver(options)

    try:
        driver.get(domain)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        html_content = driver.page_source
    except Exception as e:
        print(f"Error occurred while fetching {domain} in headless={headless} mode: {e}")

    return html_content
