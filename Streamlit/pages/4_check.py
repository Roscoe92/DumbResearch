import subprocess

def get_chrome_version():
    try:
        # Check Chromium version
        result = subprocess.run(['chromium', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        # Check Google Chrome version as a fallback
        result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        return f"Error fetching Chrome version: {e}"

def get_chromedriver_version():
    try:
        result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        return f"Error fetching ChromeDriver version: {e}"

# Example usage
if __name__ == "__main__":
    print("Chrome/Chromium Version:", get_chrome_version())
    print("ChromeDriver Version:", get_chromedriver_version())
