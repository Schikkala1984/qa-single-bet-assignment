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
from framework.pages.betting_page import BettingPage


def _euros(text: str) -> float:
    """Parse a euro amount from receipt text like 'Stake: €10.00' (handles negatives)."""
    match = re.search(r"(-?\d+(?:\.\d+)?)", text.replace(",", ""))
    assert match, f"no numeric amount found in {text!r}"
    return float(match.group(1))


@pytest.mark.ui
@pytest.mark.smoke
def test_place_single_bet_happy_path(
    betting_page: BettingPage, api: BettingApiClient, reset_balance
):
    # Arrange: pull a real match + its home odds from the API (data-driven, not hard-coded).
    match = api.matches()[0]
    match_id = match["id"]
    home_odds = float(match["odds"]["home"])
    stake = 10.0
    expected_payout = round(stake * home_odds, 2)

    # Act: load the authenticated app and read the balance once it populates.
    page = betting_page.load()
    balance_before = api.get_balance().json()["balance"]

    page.select_outcome(match_id, "home")
    page.enter_stake(str(stake))

    # Potential payout shown before committing must equal stake * odds.
    assert page.potential_payout() == pytest.approx(expected_payout, abs=0.01)

    page.place_bet()

    # Assert: the success receipt is shown with the core placement details.
    receipt = page.receipt()
    assert receipt["bet_id"], "receipt must show a Bet ID"
    assert _euros(receipt["stake"]) == pytest.approx(stake, abs=0.01)
    assert _euros(receipt["odds"]) == pytest.approx(home_odds, abs=0.01)
    assert receipt["placed_at"], "receipt must show a placement timestamp"
    page.close_success()

    # Core money invariant verified against the source of truth (the API): the bet was
    # actually placed and the stake was deducted. (The UI header's own balance refresh is
    # broken — see test_ui_balance_refreshes_after_bet / docs/execution-and-bugs.md.)
    balance_after = api.get_balance().json()["balance"]
    assert balance_after == pytest.approx(balance_before - stake, abs=0.01), (
        f"stake should be deducted server-side: {balance_before} -> {balance_after}"
    )


@pytest.mark.ui
@pytest.mark.xfail(reason="BUG: header balance does not refresh after a bet (stays stale)", strict=True)
def test_ui_balance_refreshes_after_bet(betting_page: BettingPage, api: BettingApiClient, reset_balance):
    """After a successful bet the header balance should decrease by the stake.

    Documented defect: the server balance updates but the UI header stays frozen at
    its pre-bet value. See docs/execution-and-bugs.md.
    """
    match = api.matches()[0]
    page = betting_page.load()
    before = page.balance()
    page.select_outcome(match["id"], "home")
    page.enter_stake("10")
    page.place_bet()
    page.close_success()
    assert page.balance() == pytest.approx(before - 10, abs=0.01)


@pytest.mark.ui
@pytest.mark.xfail(reason="BUG: receipt payout is wrong (shows ~stake*2, not stake*odds)", strict=True)
def test_receipt_payout_matches_odds(betting_page: BettingPage, api: BettingApiClient, reset_balance):
    """The receipt payout must equal stake x odds (10 x 2.45 = 24.50).

    Documented defect: the pre-placement 'potential payout' is correct (24.50) but
    the receipt renders a different, wrong value. See docs/execution-and-bugs.md.
    """
    match = api.matches()[0]
    page = betting_page.load()
    page.select_outcome(match["id"], "home")
    page.enter_stake("10")
    page.place_bet()
    payout = _euros(page.receipt()["payout"])
    assert payout == pytest.approx(round(10 * float(match["odds"]["home"]), 2), abs=0.01)


@pytest.mark.ui
@pytest.mark.xfail(reason="BUG: receipt lists teams reversed (away vs home)", strict=True)
def test_receipt_team_order(betting_page: BettingPage, api: BettingApiClient, reset_balance):
    """Home team must be listed first on the receipt ('Manchester Utd vs Chelsea').

    Documented defect: the receipt shows 'Chelsea vs Manchester Utd'. See
    docs/execution-and-bugs.md.
    """
    match = api.matches()[0]
    page = betting_page.load()
    page.select_outcome(match["id"], "home")
    page.enter_stake("10")
    page.place_bet()
    assert page.receipt()["match"] == f"{match['homeTeam']} vs {match['awayTeam']}"
