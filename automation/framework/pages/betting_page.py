"""Page object for the Single Bet Placement screen.

Selectors are the application's own stable element ids (e.g. `#bet-slip-place-bet`,
`#odds-<matchId>-home`, `#modal-success`), so the object maps 1:1 to the real DOM
and reads as user intent: select an outcome, enter a stake, place the bet, read the
receipt.
"""
from __future__ import annotations

import re

from selenium.webdriver.common.by import By

from ..config import settings
from .base_page import BasePage


def _euros(text: str) -> float:
    """Parse a euro amount from UI text like 'Balance: €115.50' (handles negatives)."""
    match = re.search(r"(-?\d+(?:\.\d+)?)", text.replace(",", ""))
    return float(match.group(1)) if match else 0.0


class BettingPage(BasePage):
    # Header / balance
    HEADER_BALANCE = (By.ID, "header-balance")

    # Bet slip
    STAKE_INPUT = (By.ID, "bet-slip-stake-input")
    POTENTIAL_PAYOUT = (By.ID, "bet-slip-potential-payout")
    PLACE_BET = (By.ID, "bet-slip-place-bet")

    # Success modal (receipt)
    MODAL_SUCCESS = (By.ID, "modal-success")
    MODAL_SUCCESS_BET_ID = (By.ID, "modal-success-bet-id")
    MODAL_SUCCESS_MATCH = (By.ID, "modal-success-match")
    MODAL_SUCCESS_STAKE = (By.ID, "modal-success-stake")
    MODAL_SUCCESS_ODDS = (By.ID, "modal-success-odds")
    MODAL_SUCCESS_PAYOUT = (By.ID, "modal-success-payout")
    MODAL_SUCCESS_PLACED_AT = (By.ID, "modal-success-placed-at")
    MODAL_SUCCESS_CLOSE = (By.ID, "modal-success-close")

    # ---- navigation -------------------------------------------------------
    def load(self) -> "BettingPage":
        self.open(settings.app_url)
        self.wait_for_balance_loaded()
        return self

    def wait_for_balance_loaded(self) -> None:
        """Wait until the balance XHR resolves (header shows a non-zero amount)
        rather than the initial €0.00 placeholder, so reads are not racy."""
        self.wait.until(lambda d: _euros(d.find_element(*self.HEADER_BALANCE).text) != 0.0)

    # ---- actions ----------------------------------------------------------
    def select_outcome(self, match_id: str, outcome: str) -> None:
        """outcome in {'home', 'draw', 'away'} -> clicks the 1 / X / 2 button."""
        self.click((By.ID, f"odds-{match_id}-{outcome.lower()}"))

    def enter_stake(self, stake: str) -> None:
        self.type(self.STAKE_INPUT, str(stake))

    def place_bet(self) -> None:
        self.click(self.PLACE_BET)

    def close_success(self) -> None:
        self.click(self.MODAL_SUCCESS_CLOSE)

    # ---- reads ------------------------------------------------------------
    def header_balance_text(self) -> str:
        return self.text(self.HEADER_BALANCE)

    def balance(self) -> float:
        return _euros(self.header_balance_text())

    def potential_payout(self) -> float:
        return _euros(self.text(self.POTENTIAL_PAYOUT))

    def receipt(self) -> dict[str, str]:
        self.wait_until_visible(self.MODAL_SUCCESS)
        return {
            "bet_id": self.text(self.MODAL_SUCCESS_BET_ID),
            "match": self.text(self.MODAL_SUCCESS_MATCH),
            "stake": self.text(self.MODAL_SUCCESS_STAKE),
            "odds": self.text(self.MODAL_SUCCESS_ODDS),
            "payout": self.text(self.MODAL_SUCCESS_PAYOUT),
            "placed_at": self.text(self.MODAL_SUCCESS_PLACED_AT),
        }
