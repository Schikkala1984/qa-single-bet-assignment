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
        assert body["currency"] == "EUR"
        # Payout must equal stake * odds to 2 dp.
        assert body["payout"] == pytest.approx(round(body["stake"] * body["odds"], 2), abs=0.01)
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

    Independent of the match catalog on purpose: this asserts the auth gate
    itself, so it runs even when BUG-01 blocks the authenticated endpoints.
    """
    resp = api.place_bet(match_id="any-match", selection="HOME", stake=10, with_auth=False)
    assert resp.status_code == 401, resp.text
    assert resp.json().get("error") == "missing_user_id"
