"""API test — stake validation / business-rule enforcement at the authoritative layer.

WHY THIS TEST (automation rationale):
    Stake is the money input, and the spec mandates stake rules be enforced on
    "UI + API". The API is the authoritative guard: even if the UI blocks a bad
    stake, a crafted request must still be rejected, or the business is exposed to
    malformed/out-of-range wagers. Validation is also the ideal automation
    candidate — many small, deterministic, data-driven cases that are tedious and
    slow to run by hand through a browser but near-instant and rock-solid via
    `requests`. This test pins the stake boundaries (min, max, precision, type)
    and the insufficient-balance rule.

    Assertions encode the SPECIFICATION'S expected behavior and the API's own
    documented error contract (/api/docs). If the deployment is unhealthy the
    test fails by design, which is correct — a validation guard should flag a
    backend that stops enforcing the rules.
"""
from __future__ import annotations

import pytest

from framework.api_client import BettingApiClient


@pytest.fixture(scope="module")
def match_id(api: BettingApiClient) -> str:
    return api.first_match_id()


@pytest.mark.api
@pytest.mark.parametrize(
    "stake, expect_ok, expected_error",
    [
        (1.00, True, None),            # min boundary (per API contract: >= 1.00)
        (100.00, True, None),          # max boundary
        (0.99, False, "invalid_stake_min"),
        (100.01, False, "invalid_stake_max"),
        (10.123, False, "invalid_stake_precision"),
        ("abc", False, "invalid_stake_type"),
    ],
)
def test_stake_boundary_and_precision(
    api: BettingApiClient, match_id: str, reset_balance, stake, expect_ok, expected_error
):
    resp = api.place_bet(match_id=match_id, selection="HOME", stake=stake)

    if expect_ok:
        assert resp.status_code == 200, (
            f"stake {stake!r} is valid and should be accepted, got "
            f"{resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["stake"] == pytest.approx(float(stake))
    else:
        assert resp.status_code == 422, (
            f"stake {stake!r} is invalid and should be rejected with 422, got "
            f"{resp.status_code}: {resp.text}"
        )
        assert resp.json().get("error") == expected_error


@pytest.mark.api
def test_invalid_selection_is_rejected(api: BettingApiClient, match_id: str, reset_balance):
    """Selection must be one of HOME/DRAW/AWAY; a forged value is a 422."""
    resp = api.place_bet(match_id=match_id, selection="SIDEWAYS", stake=10)
    assert resp.status_code == 422, resp.text
    assert resp.json().get("error") == "invalid_selection"


@pytest.mark.api
def test_missing_user_context_is_unauthorized(api: BettingApiClient):
    """No x-user-id -> request must never touch the money path.

    Independent of the match catalog on purpose: this asserts the auth gate itself.
    """
    resp = api.place_bet(match_id="any-match", selection="HOME", stake=10, with_auth=False)
    assert resp.status_code == 401, resp.text
    assert resp.json().get("error") == "missing_user_id"


# --- Known defects, encoded as expected failures ---------------------------
# These assert the SPEC-correct behavior and are marked xfail because the live
# API currently violates it. They are documented in docs/execution-and-bugs.md.
# When the backend is fixed, xfail flips to XPASS and flags that the guard can
# be promoted to a hard assertion. This keeps the suite green while still
# encoding the bugs as executable, self-documenting checks.

@pytest.mark.api
@pytest.mark.xfail(reason="BUG: place-bet returns currency 'USD'; spec requires EUR", strict=True)
def test_placebet_currency_is_eur(api: BettingApiClient, match_id: str, reset_balance):
    resp = api.place_bet(match_id=match_id, selection="HOME", stake=10)
    assert resp.status_code == 200, resp.text
    assert resp.json()["currency"] == "EUR"


@pytest.mark.api
@pytest.mark.xfail(reason="BUG: payout truncates instead of rounding (12.5*4.1 -> 51.24, want 51.25)", strict=True)
def test_payout_is_rounded_not_truncated(api: BettingApiClient, reset_balance):
    # serie-a-juve-milan AWAY odds = 4.1; 12.5 * 4.1 = 51.249999..., should round to 51.25
    resp = api.place_bet(match_id="serie-a-juve-milan", selection="AWAY", stake=12.5)
    assert resp.status_code == 200, resp.text
    assert resp.json()["payout"] == pytest.approx(51.25, abs=0.001)
