# QA Engineer Home Assignment — Single Bet Placement

QA deliverables for the **Single Bet Placement** feature of the Sports Betting app at
`https://qae-assignment-tau.vercel.app/`. The work is grounded in real exploration of the live
application and its API (`/api/docs`), not just the written spec.

## What's here

| Part | Deliverable | Location |
|------|-------------|----------|
| A.1 | Test plan — 6 prioritized scenarios with risk rationale | [`docs/test-plan.md`](docs/test-plan.md) |
| A.2 | Execution results + bug reports (with evidence) | [`docs/execution-and-bugs.md`](docs/execution-and-bugs.md) |
| B | Automation framework (Selenium + Pytest + requests) + 2 tests + README | [`automation/`](automation/) |
| C | Strategy & recommendations | [`docs/strategy-and-recommendations.md`](docs/strategy-and-recommendations.md) |
| — | CI pipeline (API on push, UI on PR/nightly) | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |

## Headline findings (details in `docs/execution-and-bugs.md`)

- **BUG-01 (Critical):** No `user-id` authenticates against the deployed API — every value returns
  `401 invalid_user_id`, so balance, matches, and bet placement are all unreachable. The core product
  is a total outage. Reproduced via direct API calls (~75 values) and through the app's own UI in a
  real browser.
- **BUG-02 (Medium):** `GET /api/place-bet` returns `200 {}` instead of `405 method_not_allowed`
  (`PUT`/`DELETE` on the same route correctly return `405`).
- **Spec clarification:** minimum stake is stated as both €1.00 (Business Rules) and €1.01
  (Validation table); the API says "at least 1.00".

## Quick start

```bash
cd automation
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -m api        # fast API checks
pytest -m ui         # UI journey (launches Chrome)
```

See [`automation/README.md`](automation/README.md) for full setup, configuration, and the note on how
the tests behave against the currently-broken deployment.

## Approach

Correctness and risk-based prioritization over volume. Scenarios are chosen for the risk they buy
down (can't bet / wrong charge / lying receipt / bad validation), split deliberately across UI and
API layers. The automation asserts the **specification's expected** behavior and reads the target
`user-id`/`BASE_URL` from config, so it is immediately reusable across environments and will pass
automatically once the backend serves a valid user.
