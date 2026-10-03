"""Base page object: shared Selenium interaction helpers.

Every page object inherits explicit-wait based helpers so tests never sprinkle
`time.sleep`. Waits key off element conditions, which is what makes a Selenium
suite stable instead of flaky.
"""
from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..config import settings


class BasePage:
    def __init__(self, driver: WebDriver, timeout: int | None = None):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout or settings.timeout)

    def open(self, url: str) -> None:
        self.driver.get(url)

    def find(self, locator: tuple[str, str]) -> WebElement:
        return self.wait.until(EC.presence_of_element_located(locator))

    def click(self, locator: tuple[str, str]) -> None:
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def type(self, locator: tuple[str, str], value: str) -> None:
        el = self.wait.until(EC.visibility_of_element_located(locator))
        el.clear()
        el.send_keys(value)

    def text(self, locator: tuple[str, str]) -> str:
        return self.find(locator).text.strip()

    def wait_until_visible(self, locator: tuple[str, str]) -> WebElement:
        return self.wait.until(EC.visibility_of_element_located(locator))
