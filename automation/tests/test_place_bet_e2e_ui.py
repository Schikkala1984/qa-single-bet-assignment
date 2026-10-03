"""E2E UI test — the critical user journey: place a single bet and verify the receipt.

WHY THIS TEST (automation rationale):
    This is the one journey the product exists to deliver and the only one that
    exercises the full money path through the real UI: authenticate -> see balance
    -> select an outcome -> stake -> place -> success receipt -> balance deducted.
    It is the highest-value regression guard: if it goes red, the product is not
    shippable. Driving it through Selenium (not the API) is deliberate, because the
    risk being bought down here is specifically the *browser* experience — the slip
    wiring, the loading state, and that the receipt the user sees is correct and
    consistent with the balance.
"""
from __future__ import annotations

import re

import pytest

from framework.api_client import BettingApiClient
from framework.config import settings
from framework.pages.betting_page import BettingPage


def _euros(text: str) -> float:
    """Extract a numeric euro amount from UI text like 'Balance: €115.50'."""
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    assert match, f"no numeric amount found in {text!r}"
    return float(match.group(1))


@pytest.mark.ui
@pytest.mark.smoke
def test_place_single_bet_happy_path(
    betting_page: BettingPage, api: BettingApiClient, reset_balance
):
    # Arrange: get a real match + its home odds from the API (data-driven, not hard-coded).
    match = api.matches()[0]
    match_id = match["id"]
    home_odds = float(match["odds"]["home"])
    stake = 10.0
    expected_payout = round(stake * home_odds, 2)

    # Act
    page = betting_page.load()
    starting = _euros(page.header_balance_text())
    assert starting == pytest.approx(settings.starting_balance), (
        f"expected fresh balance {settings.starting_balance}, saw {starting}"
    )

    page.select_outcome(match_id, "home")
    page.enter_stake(str(stake))

    # Potential payout shown before committing must equal stake * odds.
    assert _euros(page.potential_payout_text()) == pytest.approx(expected_payout, abs=0.01)

    page.place_bet()

    # Assert: success receipt is shown with consistent values.
    receipt = page.receipt()
    assert receipt["bet_id"], "receipt must show a Bet ID"
    assert _euros(receipt["stake"]) == pytest.approx(stake, abs=0.01)
    assert _euros(receipt["odds"]) == pytest.approx(home_odds, abs=0.01)
    assert _euros(receipt["payout"]) == pytest.approx(expected_payout, abs=0.01)
    assert receipt["placed_at"], "receipt must show a placement timestamp"

    # And the balance is deducted by exactly the stake.
    page.close_success()
    ending = _euros(page.header_balance_text())
    assert ending == pytest.approx(starting - stake, abs=0.01), (
        f"balance should drop by stake {stake}: {starting} -> {ending}"
    )
