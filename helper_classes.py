from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from setup_gologin import start_remote_debug_gologin_browser



class BrowserManager:
    def __init__(self):
        self.driver = None
        self.gl = None

    def start_browser_session(self):
        driver,gl = start_remote_debug_gologin_browser()
        driver.implicitly_wait(1)
        self.driver = driver
        self.gl = gl

    def stop_browser_session(self):
        self.driver.quit()
        self.gl.stop()

    def restart_browser_session(self):
        self.stop_browser_session()
        self.start_browser_session()


def try_except_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"An exception occurred: {e}")
    return wrapper


class ElementFinder:
    def __init__(self, driver: WebElement):
        self.driver = driver

    #@try_except_decorator
    def find_by_xpath(self, xpath):
       return self.driver.find_element(By.XPATH, xpath)
    
    #@try_except_decorator
    def find_list_by_xpath(self, xpath):
        return self.driver.find_elements(By.XPATH, xpath)

    #@try_except_decorator
    def find_by_class(self, class_):
        return self.driver.find_element(By.CLASS_NAME, class_)

    #@try_except_decorator
    def find_list_by_class(self, class_):
        return self.driver.find_elements(By.CLASS_NAME, class_)