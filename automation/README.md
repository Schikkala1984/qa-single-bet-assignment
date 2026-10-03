# Part B — Automation Framework

A small, focused Selenium + Pytest + `requests` framework for the Single Bet Placement
feature. Two high-value tests ship with it: one **E2E UI** critical-journey test and one
**API** validation/business-rule test. The framework is built to be read and extended, not
just to run two cases.

## Tech & tooling choices

| Concern | Choice | Why |
|--------|--------|-----|
| Language | Python 3.9+ | Required stack. |
| UI automation | Selenium WebDriver 4 | Required stack. Page Object Model for maintainability. |
| Test runner | Pytest | Required stack. Fixtures + parametrize keep tests declarative. |
| API testing | `requests` | Required stack. Wrapped in a typed client so tests read as intent. |
| Driver management | `webdriver-manager` | Auto-matches chromedriver to the installed Chrome — zero manual setup / no committed binaries. |
| Config | `python-dotenv` (optional) + env vars | 12-factor config; no secrets or URLs hard-coded. |

## Project structure

```
automation/
├── conftest.py                 # Pytest fixtures: api client, Chrome driver, balance reset
├── pytest.ini                  # Markers (api/ui/smoke), logging, strict config
├── requirements.txt
├── .env.example                # Copy to .env to override BASE_URL / USER_ID / HEADLESS
├── framework/
│   ├── config.py               # Env-driven settings + known business rules (single source of truth)
│   ├── api_client.py           # Typed wrapper over the REST API (auth header injected)
│   └── pages/
│       ├── base_page.py        # Explicit-wait Selenium helpers (no sleeps)
│       └── betting_page.py     # Page Object using the app's real element ids
└── tests/
    ├── test_place_bet_e2e_ui.py        # E2E UI: critical journey + receipt + balance
    └── test_place_bet_validation_api.py # API: stake boundaries, precision, selection, auth
```

**Design principles**
- **Page Object Model** — selectors live in `betting_page.py` using the app's own stable
  element ids (`#bet-slip-place-bet`, `#odds-<matchId>-home`, `#modal-success-*`). Tests express
  behavior, never raw locators.
- **Explicit waits only** — `base_page.py` keys off element conditions; there is no `time.sleep`,
  which is the usual source of Selenium flakiness.
- **Config in one place** — `config.py` resolves `BASE_URL`, `USER_ID`, `HEADLESS`, `TIMEOUT`
  from the environment and also holds the known business rules used in assertions.
- **Data-driven** — the UI test reads a real match + odds from the API rather than hard-coding,
  so it survives catalog changes.

## Setup

Prerequisites: **Python 3.9+** and a recent desktop **Chrome**.

```bash
cd automation
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env            # then edit USER_ID / HEADLESS if needed
```

## Running the tests

```bash
# Everything
pytest

# API tests only (fast, no browser)
pytest -m api

# UI tests only (launches Chrome)
pytest -m ui

# Smoke (the single critical journey)
pytest -m smoke

# Watch the browser locally
HEADLESS=false pytest -m ui          # PowerShell: $env:HEADLESS="false"; pytest -m ui
```

Override the target without touching code:

```bash
# PowerShell
$env:USER_ID="some_user"; $env:BASE_URL="https://qae-assignment-tau.vercel.app"; pytest
```

## Important: current state of the target deployment

During exploration the deployed API returned `401 invalid_user_id` for **every** user-id value
tried (see `../docs/execution-and-bugs.md`, BUG-01). The tests assert the **specification's
expected** behavior, so against the current (broken) deployment the authenticated tests will
**fail by design** — a validation suite *should* flag a backend that stops enforcing the contract.
As soon as a working `USER_ID` is supplied (or the backend is fixed), the suite passes with no code
changes: set `USER_ID` and re-run.
