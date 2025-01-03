from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import shutil

def test_selenium():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    service = Service(executable_path=shutil.which("chromedriver"))

    try:
        driver = webdriver.Chrome(options=options, service=service)
        driver.get("https://www.google.com")
        print("Successfully launched Chrome.")
        print(f"Page title: {driver.title}")
        driver.quit()
    except Exception as e:
        print(f"Error: {e}")

test_selenium()
