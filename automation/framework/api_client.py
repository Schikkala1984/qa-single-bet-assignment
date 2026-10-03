"""Thin, typed wrapper around the Sports Betting REST API.

Keeping all HTTP concerns in one place means tests read as business intent
("place a bet", "get balance") rather than URL/header plumbing. The client
injects the `x-user-id` auth header automatically and exposes the raw
`requests.Response` so tests can assert on status codes and bodies precisely.
"""
from __future__ import annotations

from typing import Any

import requests

from .config import settings


class BettingApiClient:
    def __init__(self, base_url: str | None = None, user_id: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or settings.base_url).rstrip("/")
        self.user_id = user_id if user_id is not None else settings.user_id
        self.timeout = timeout or settings.timeout
        self._session = requests.Session()

    # -- header helpers -----------------------------------------------------
    def _headers(self, with_auth: bool = True) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if with_auth and self.user_id is not None:
            headers["x-user-id"] = self.user_id
        return headers

    # -- endpoints ----------------------------------------------------------
    def get_matches(self, with_auth: bool = True) -> requests.Response:
        return self._session.get(
            f"{self.base_url}/api/matches",
            headers=self._headers(with_auth),
            timeout=self.timeout,
        )

    def get_balance(self, with_auth: bool = True) -> requests.Response:
        return self._session.get(
            f"{self.base_url}/api/balance",
            headers=self._headers(with_auth),
            timeout=self.timeout,
        )

    def place_bet(
        self,
        match_id: str,
        selection: str,
        stake: Any,
        with_auth: bool = True,
    ) -> requests.Response:
        """Place a single bet. `stake` is passed through as-is so negative tests
        can send non-numeric values (e.g. "abc") to exercise type validation."""
        return self._session.post(
            f"{self.base_url}/api/place-bet",
            json={"matchId": match_id, "selection": selection, "stake": stake},
            headers=self._headers(with_auth),
            timeout=self.timeout,
        )

    def reset_balance(self, with_auth: bool = True) -> requests.Response:
        return self._session.post(
            f"{self.base_url}/api/reset-balance",
            headers=self._headers(with_auth),
            timeout=self.timeout,
        )

    # -- convenience --------------------------------------------------------
    def matches(self) -> list[dict[str, Any]]:
        """Return the match list, with a clear diagnostic if auth is rejected.

        Raises a readable error (rather than a cryptic KeyError) when the
        environment is in the BUG-01 state where no user-id authenticates.
        """
        resp = self.get_matches()
        if resp.status_code == 401:
            raise AssertionError(
                f"Cannot load matches: {resp.status_code} {resp.text}. "
                f"The user-id '{self.user_id}' was rejected (see docs/execution-and-bugs.md, "
                f"BUG-01). Set a valid USER_ID and re-run."
            )
        resp.raise_for_status()
        data = resp.json()
        assert isinstance(data, list) and data, f"expected a non-empty match list, got {data!r}"
        return data

    def first_match_id(self) -> str:
        return self.matches()[0]["id"]
