"""Shared pytest fixtures: the API client and a managed Chrome WebDriver.

The WebDriver fixture auto-installs a matching chromedriver via webdriver-manager
so the suite runs on any machine with Chrome and no manual driver setup. A
`reset_balance` fixture gives money-path tests a known starting balance.
"""
from __future__ import annotations

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from framework.api_client import BettingApiClient
from framework.config import settings
from framework.pages.betting_page import BettingPage


@pytest.fixture(scope="session")
def api() -> BettingApiClient:
    return BettingApiClient()


@pytest.fixture()
def reset_balance(api: BettingApiClient):
    """Reset to the configured starting balance so money assertions are deterministic."""
    api.reset_balance()
    yield
    api.reset_balance()


@pytest.fixture()
def driver():
    options = Options()
    if settings.headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    service = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=service, options=options)
    drv.implicitly_wait(0)  # we use explicit waits only
    yield drv
    drv.quit()


@pytest.fixture()
def betting_page(driver) -> BettingPage:
    return BettingPage(driver)
