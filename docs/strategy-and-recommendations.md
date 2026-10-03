# Part C — Strategy & Recommendations

## Why I automated these two tests

**1. E2E UI — place a single bet (critical journey).**
This is the product's reason to exist and the only flow that exercises the entire money path
through the real browser: authenticate → balance → select outcome → stake → place → receipt →
balance deducted. Automating it gives the highest return per line of test code: a single red run
means "not shippable". It also guards the parts that *only* break in the UI — the slip wiring, the
`Placing...` loading state, and receipt↔balance consistency — which an API test can't see.

**2. API — stake validation & business rules.**
Stake is the money input and the spec requires enforcement on "UI + API". The API is the
authoritative guard: a crafted request must be rejected even if the UI would have blocked it.
Validation is also the *ideal* automation shape — many small, deterministic, data-driven cases
(min, max, precision, type, forged selection, missing auth) that are tedious and slow by hand but
instant and stable through `requests`. One parametrized test covers boundaries that would be a dozen
manual steps.

Together they cover the two risk buckets that matter most — "can the user bet at all and get a
correct receipt" (UI) and "can a bad bet get through" (API) — across two layers, with almost no
overlap.

## What I intentionally left as manual-only, and why

- **Visual / layout / responsive polish** of the bet slip, modals, and match cards. Cheap and
  reliable for a human to eyeball; expensive and brittle to assert pixel-by-pixel in Selenium.
  Better served later by dedicated visual-diff tooling than by functional automation.
- **Exploratory testing around the bet flow** (odd stake inputs, rapid re-selection, double-click
  Place Bet, back-button mid-placement, 409 "bet already in progress" races). This is where novel,
  high-impact bugs are actually found; scripting it first would freeze the thinking that makes it
  valuable. Once a concrete bug is found, it graduates into an automated regression case.
- **Error-modal retry/close UX** (`Rebet` vs `Close` vs top-right `X`). Worth a scripted check
  eventually, but it needs a reliable way to force a placement failure (fault injection / a stub).
  Until that hook exists, automating it means relying on real server errors, which is flaky — so it
  stays manual for now.
- **The reset-balance consistency claim.** The live Swagger literally says the reset "response
  payload may differ from persisted balance". That is a verification/oracle question best confirmed
  by a human first (balance before vs after, response vs a follow-up `GET /api/balance`) before being
  pinned as an automated invariant.

## Top recommendations if this project scaled

1. **CI/CD with layered gating and a test data strategy.** Run `pytest -m api` on every push (fast,
   headless, no browser) and `pytest -m "ui or smoke"` on PRs and nightly, in GitHub Actions with a
   Chrome service and the HTML/Allure report published as an artifact. Crucially, give tests a
   **deterministic data seam**: `POST /api/reset-balance` already exists — make each money-path test
   own its state via reset (as the fixtures do) and run per-user-id so parallel runs don't collide.
   Add a pre-flight auth smoke check that fails the pipeline fast with a clear message if the
   environment rejects the configured user-id (which is exactly the BUG-01 situation).

2. **Push coverage down the pyramid and add a contract test.** The suite is intentionally thin at the
   top (one UI journey). As it grows, keep most new coverage at the API/`requests` layer (status codes,
   error taxonomy, payout math, idempotency/409) and add a **contract test that validates live
   responses against the published OpenAPI** (`/api/docs?format=json`). That catches drift like
   `GET /api/place-bet` returning `200 {}` instead of `405` (BUG-02) automatically, instead of relying
   on someone writing a bespoke assertion.

3. **Resolve spec ambiguities and add observability for money.** Fix the minimum-stake contradiction
   (Business Rules say €1.00, the validation table says €1.01, the API says "at least 1.00") so the
   boundary has one true answer. For a real betting product, I'd also want structured logging/alerting
   on auth-failure rate and placement success rate — the current total-auth-outage (BUG-01) is exactly
   the kind of thing a "placement success rate dropped to 0%" alert should have caught before a user did.
