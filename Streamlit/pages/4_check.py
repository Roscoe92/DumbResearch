import subprocess
import streamlit as st

def check_environment():
    try:
        # Check Chromium version
        chromium_version = subprocess.run(
            ["chromium", "--version"], capture_output=True, text=True
        )
        chromium_output = chromium_version.stdout.strip() or chromium_version.stderr.strip()

        # Check ChromeDriver version
        chromedriver_version = subprocess.run(
            ["chromedriver", "--version"], capture_output=True, text=True
        )
        chromedriver_output = chromedriver_version.stdout.strip() or chromedriver_version.stderr.strip()

        # Display results in Streamlit
        st.write("**Chromium Version:**", chromium_output)
        st.write("**ChromeDriver Version:**", chromedriver_output)

        # Check executable paths
        chromium_path = subprocess.run(
            ["which", "chromium"], capture_output=True, text=True
        ).stdout.strip()
        chromedriver_path = subprocess.run(
            ["which", "chromedriver"], capture_output=True, text=True
        ).stdout.strip()

        st.write("**Chromium Path:**", chromium_path)
        st.write("**ChromeDriver Path:**", chromedriver_path)

    except Exception as e:
        st.error(f"Error checking environment: {e}")

# Run the check
check_environment()
