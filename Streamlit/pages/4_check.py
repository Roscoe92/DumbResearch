import streamlit as st
from scraper.scraper import run_selenium
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def get_driver():
    return webdriver.Chrome(
        service=Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        ))

def main():
    driver = get_driver()
    if st.button("Fetch Subpages"):
        result = driver.get()
        st.session_state.result = result

    if st.session_state.result:
        st.write(st.session_state.result)

# Run the app
if __name__ == "__main__":
    main()

# def get_webdriver_options(headless=False):
#     options = Options()
#     if headless:
#         options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")  # Required for environments with small /dev/shm
#     options.add_argument("--disable-gpu")           # Avoid GPU issues
#     options.add_argument("--window-size=1920x1080") # Ensure sufficient resolution for rendering
#     options.add_argument("--disable-software-rasterizer")
#     options.add_argument("--disable-extensions")
#     options.add_argument("--remote-debugging-port=9222")  # Ensure DevToolsActivePort can connect
#     options.add_argument("--disable-background-timer-throttling")
#     options.add_argument("--disable-renderer-backgrounding")
#     options.add_argument("--disable-background-networking")
#     return options

# def get_webdriver_service():
#     service = Service(
#             ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
#         )
#     return service

# def get_driver():
#     driver = webdriver.Chrome(service=get_webdriver_service(), options = get_webdriver_options())
#     return driver

#     options = Options()
#     options.add_argument("--disable-gpu")
#     options.add_argument("--headless")

#     driver = get_driver()
#     driver.get("http://example.com")

#     st.code(driver.page_source)


# def main():
#     # Initialize `links` in session state if not already set
#     if "links" not in st.session_state:
#         st.session_state["links"] = []

#     # Input field for website
#     check_site = st.text_input(
#         "Add any additional competitors by entering their websites (comma-separated):"
#     )

#     # Button to fetch subpages
#     if st.button("Fetch Subpages"):
#         if check_site:  # Ensure `check_site` is not empty
#             driver = get_driver()
#             links = driver.get(check_site)
#             st.session_state["links"] = links  # Update session state
#             st.success("Subpages fetched successfully!")
#         else:
#             st.warning("Please enter a valid website.")

#     # Display results if available
#     if st.session_state["links"]:
#         st.write("Fetched Links:")
#         st.write(st.session_state["links"])
#     else:
#         st.write("No links fetched yet.")

#     # Check for ChromeDriver log and provide download option
#     if os.path.exists("chromedriver.log"):
#         st.download_button(
#             label="Download ChromeDriver Log",
#             data=open("chromedriver.log", "rb"),
#             file_name="chromedriver.log",
#             mime="text/plain"
#         )
#     else:
#         st.warning("ChromeDriver log file not found.")

# # Run the app
# if __name__ == "__main__":
#     main()
