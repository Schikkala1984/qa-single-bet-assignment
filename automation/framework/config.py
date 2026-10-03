"""Central, environment-driven configuration.

All knobs live here so tests never hard-code URLs, credentials, or timeouts.
Values are read from the environment (optionally via a local .env file) and fall
back to sensible defaults for the assignment's target app.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    # Optional: load a local .env if python-dotenv is installed.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience, not a requirement
    pass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable test settings resolved once at import time."""

    base_url: str = os.getenv("BASE_URL", "https://qae-assignment-tau.vercel.app").rstrip("/")
    user_id: str = os.getenv("USER_ID", "chikkala-srinivas")
    headless: bool = _as_bool(os.getenv("HEADLESS", "true"))
    timeout: int = int(os.getenv("TIMEOUT", "15"))

    # Known business rule from the spec, asserted by the UI happy-path test.
    starting_balance: float = 125.50

    @property
    def app_url(self) -> str:
        """The UI entry point including the authenticating query parameter."""
        return f"{self.base_url}/?user-id={self.user_id}"


settings = Settings()
