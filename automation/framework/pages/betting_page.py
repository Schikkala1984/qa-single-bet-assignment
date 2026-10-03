"""Page object for the Single Bet Placement screen.

Selectors are the application's own stable element ids (e.g. `#bet-slip-place-bet`,
`#odds-<matchId>-home`, `#modal-success`), so the object maps 1:1 to the real DOM
and reads as user intent: select an outcome, enter a stake, place the bet, read the
receipt.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from ..config import settings
from .base_page import BasePage


class BettingPage(BasePage):
    # Header / balance
    HEADER_BALANCE = (By.ID, "header-balance")
    AUTH_ERROR = (By.ID, "auth-error")
    MATCH_LIST = (By.ID, "match-list")
    MATCH_LIST_COUNT = (By.ID, "match-list-count")

    # Bet slip
    SLIP = (By.ID, "bet-slip")
    SLIP_BALANCE = (By.ID, "bet-slip-balance")
    STAKE_INPUT = (By.ID, "bet-slip-stake-input")
    POTENTIAL_PAYOUT = (By.ID, "bet-slip-potential-payout")
    PLACE_BET = (By.ID, "bet-slip-place-bet")
    REMOVE_ALL = (By.ID, "bet-slip-remove-all")

    # Success modal
    MODAL_SUCCESS = (By.ID, "modal-success")
    MODAL_SUCCESS_BET_ID = (By.ID, "modal-success-bet-id")
    MODAL_SUCCESS_MATCH = (By.ID, "modal-success-match")
    MODAL_SUCCESS_STAKE = (By.ID, "modal-success-stake")
    MODAL_SUCCESS_ODDS = (By.ID, "modal-success-odds")
    MODAL_SUCCESS_PAYOUT = (By.ID, "modal-success-payout")
    MODAL_SUCCESS_PLACED_AT = (By.ID, "modal-success-placed-at")
    MODAL_SUCCESS_CLOSE = (By.ID, "modal-success-close")

    # Error modal
    MODAL_ERROR = (By.ID, "modal-error")
    MODAL_ERROR_MESSAGE = (By.ID, "modal-error-message")
    MODAL_ERROR_REBET = (By.ID, "modal-error-rebet")

    # ---- navigation -------------------------------------------------------
    def load(self) -> "BettingPage":
        self.open(settings.app_url)
        return self

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

    def potential_payout_text(self) -> str:
        return self.text(self.POTENTIAL_PAYOUT)

    def success_modal_shown(self) -> bool:
        return self.is_visible(self.MODAL_SUCCESS)

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
