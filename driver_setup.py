import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

def get_webdriver():
    """
    Initializes and returns a Selenium WebDriver instance using the local chromedriver.
    It combines configurations from both main.py and detail parsers.
    Handles both script execution and PyInstaller bundled execution.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-gpu")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # Path setup
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running as a normal script
        # Assumes driver_setup.py is at the project root
        base_path = os.path.abspath(".")
        
    chrome_driver_path = os.path.join(base_path, "assets", "chromedriver.exe")
    
    if not os.path.exists(chrome_driver_path):
        raise FileNotFoundError(f"ChromeDriver not found at the specified path: {chrome_driver_path}")

    service = Service(executable_path=chrome_driver_path)
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except WebDriverException as e:
        # Re-raise the exception to be handled by the caller
        raise WebDriverException(f"Failed to create WebDriver: {e.msg}") 