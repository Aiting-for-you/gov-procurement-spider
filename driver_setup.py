import undetected_chromedriver as uc
import sys
import os
from selenium.common.exceptions import WebDriverException

# A global reference to prevent premature garbage collection
_global_driver_ref = None

class WebDriverManager:
    _driver = None

    @classmethod
    def get_webdriver(cls):
        """
        Returns a globally unique instance of the webdriver.
        If the driver doesn't exist or has been quit, it creates a new one.
        """
        global _global_driver_ref
        if cls._driver is None:
            print("[WebDriverManager] No active driver found. Creating a new one.")
            try:
                options = uc.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument("window-size=1920,1080")
                
                # undetected_chromedriver handles driver management automatically
                cls._driver = uc.Chrome(options=options, version_main=114)
                _global_driver_ref = cls._driver # Assign to global reference
                print(f"[WebDriverManager] New driver created with ID: {id(cls._driver)}")
            except Exception as e:
                print(f"[WebDriverManager] Failed to create webdriver: {e}")
                raise
        return cls._driver

    @classmethod
    def quit_webdriver(cls):
        """
        Quits the globally managed webdriver instance if it exists.
        """
        global _global_driver_ref
        if cls._driver is not None:
            print(f"[WebDriverManager] Quitting driver with ID: {id(cls._driver)}")
            try:
                cls._driver.quit()
            except Exception as e:
                print(f"[WebDriverManager] Error while quitting driver: {e}")
            finally:
                cls._driver = None
                _global_driver_ref = None # Clear the global reference
                print("[WebDriverManager] Driver has been quit and instance is reset to None.")

# For backward compatibility, we can provide top-level functions
def get_webdriver():
    return WebDriverManager.get_webdriver()

def quit_webdriver():
    WebDriverManager.quit_webdriver()

def get_webdriver():
    """
    Initializes and returns a Selenium WebDriver instance using undetected-chromedriver
    to avoid bot detection.
    """
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument("window-size=1920,1080")
        
        # undetected_chromedriver handles driver management automatically
        driver = uc.Chrome(options=options)
        return driver
        
    except Exception as e:
        print(f"初始化 (undetected) WebDriver 时出错: {e}")
        # Re-raise a generic exception that the caller can handle
        raise WebDriverException(f"Failed to create undetected WebDriver: {e}") 