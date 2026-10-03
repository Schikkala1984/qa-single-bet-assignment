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

The core journey works (a bet places and the stake is deducted server-side), but exploration found
several money-handling defects — the highest-impact class for a betting product:

- **BUG-01 (Critical):** stakes exceeding the balance are accepted; the balance goes **negative**
  (€20 balance + €100 bet → balance `-80`). No insufficient-balance enforcement.
- **BUG-02 (Critical):** the success **receipt shows the wrong payout** (€20.00 for a €10 bet at odds
  2.45; correct = €24.50 — and the pre-placement slip shows €24.50).
- **BUG-03 (High):** `reset-balance` is **inconsistent** — response says `125.5`, persisted value is
  `120` — and resets to the wrong amount.
- **BUG-04 (High):** the **UI balance never refreshes** after a bet (server updates, header stays stale).
- Plus: `place-bet` currency `USD` not `EUR`, payout truncation (51.24 vs 51.25), receipt teams
  reversed, `GET /api/place-bet`→`200`, malformed JSON→`500`.
- **Spec clarification:** minimum stake is stated as both €1.00 (Business Rules) and €1.01
  (Validation table); the API says "at least 1.00".

## Quick start

```bash
cd automation
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -m api        # fast API checks        -> 8 passed, 2 xfailed
pytest -m ui         # UI journey (Chrome)    -> 1 passed, 3 xfailed
```

The `xfailed` cases are the known defects above, encoded as strict expected-failures so the suite
stays green while the bugs remain executable and documented. See
[`automation/README.md`](automation/README.md) for setup and the auth note (use your issued user-id).

## Approach

Correctness and risk-based prioritization over volume. Scenarios are chosen for the risk they buy
down (can't bet / wrong charge / lying receipt / bad validation), split deliberately across UI and
API layers. The automation reads the target `user-id`/`BASE_URL` from config, so it is reusable
across environments; known product bugs are captured as `xfail` checks that will flip to failures
(prompting promotion to hard assertions) once fixed.
