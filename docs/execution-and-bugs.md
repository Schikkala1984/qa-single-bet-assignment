# Part A.2 — Execution Results & Bug Reports

**Application:** https://qae-assignment-tau.vercel.app/?user-id=candidate-pGM9TBT3AEsq
**Date executed:** 2026-10-03
**Method:** The flow was executed through the application UI in a real Chrome browser
(Selenium) and corroborated at the API layer with direct `requests`/HTTP calls. Every status
code, response body, and on-screen value quoted below is a verbatim observation.

> Scoring note: not scored on bug count, so this focuses on the high-impact issues. The
> money-handling defects (BUG-01, BUG-02, BUG-03, BUG-04) are the ones that matter — each one
> either lets the user lose/gain money incorrectly or misreports money to them.

---

## Execution results — Top 3 priority scenarios

| Scenario | Result | Evidence / notes |
|----------|--------|------------------|
| **TC-01** Place a valid single bet (happy path) | **PASS (core) with defects** | Bet places successfully, receipt appears (Bet ID `#B-29305`, stake €10.00, odds 2.45, timestamp), stake is deducted server-side (€125.50→€115.50 on a clean balance). BUT the receipt payout and team order are wrong, and the UI balance does not refresh — see BUG-02, BUG-05, BUG-04. Evidence: `evidence/03-receipt-BUG-payout-and-team-order.png`. |
| **TC-02** Authentication enforced | **PASS** | Missing `x-user-id` → `401 missing_user_id`; a valid issued id → `200` with balance €125.50 and the match list. Behaves per spec. |
| **TC-03** Stake boundary & precision (API) | **PASS** | `1.00`/`100.00` accepted; `0.99`→`422 invalid_stake_min`; `100.01`→`422 invalid_stake_max`; `10.123`→`422 invalid_stake_precision`; `"abc"`→`422 invalid_stake_type`. Error taxonomy matches the spec/Swagger. |

Quick exploratory testing around the flow (insufficient balance, reset, methods, malformed
payloads, concurrency, receipt consistency) surfaced the defects below.

---

## BUG-01 — Bets exceeding the balance are accepted; balance goes negative

- **Severity:** Critical
- **Component:** `POST /api/place-bet` — balance/affordability enforcement
- **Reproduction Steps:**
  1. `POST /api/reset-balance` (balance → €120 persisted; see BUG-03).
  2. `POST /api/place-bet` `{matchId:"la-liga-real-barca", selection:"HOME", stake:100}` → `200`, balance `20`.
  3. `POST /api/place-bet` same body again (stake 100 on a €20 balance) → **`200` Bet placed successfully, balance `-80`**.
  4. Repeating drives the balance further negative (`-85`, …).
- **Expected vs Actual:**
  - **Expected (spec §4.1):** a stake exceeding the available balance is rejected ("Insufficient balance" / `insufficient_balance`); balance never goes below 0.
  - **Actual:** the bet is accepted and the balance becomes negative. No `insufficient_balance` path is ever hit.
- **Business Impact:** Users can wager money they do not have; the book takes on unbounded, unfunded liability and pays out on stakes that were never covered. This is the most financially dangerous defect in the system.
- **Evidence:** HTTP responses captured in step 2–3 (`balance:-80`).

## BUG-02 — Success receipt shows the wrong payout

- **Severity:** Critical
- **Component:** Success receipt modal (`#modal-success-payout`)
- **Reproduction Steps:**
  1. Reset balance, open the app with the issued id.
  2. Select Manchester Utd vs Chelsea → Home (odds **2.45**), stake **€10**.
  3. Bet slip "Potential Payout" correctly shows **€24.50** (10 × 2.45).
  4. Click Place Bet; read the receipt "Potential Payout".
- **Expected vs Actual:**
  - **Expected:** receipt payout = stake × odds = **€24.50**, consistent with the slip.
  - **Actual:** receipt payout shows **€20.00**.
- **Business Impact:** The receipt is the user's record of the contract. Showing a payout that differs from both the formula and the pre-placement figure is a direct trust/dispute and potential-liability problem.
- **Evidence:** `evidence/03-receipt-BUG-payout-and-team-order.png` (slip €24.50 vs receipt €20.00).

## BUG-03 — `reset-balance` is inconsistent and resets to the wrong value

- **Severity:** High
- **Component:** `POST /api/reset-balance` / balance persistence
- **Reproduction Steps:**
  1. `POST /api/reset-balance` → `200 {"balance":125.5,"currency":"EUR"}`.
  2. Immediately `GET /api/balance` → `{"balance":120,"currency":"EUR"}`.
  3. Repeat — reproduces 3/3.
- **Expected vs Actual:**
  - **Expected (spec §5.3):** reset restores the initial configured balance (**€125.50**) and the response body is consistent with persisted state.
  - **Actual:** the reset response says `125.5` but the persisted/queried balance is `120`. Two problems: (a) response ≠ persisted state, (b) the reset value itself is wrong (120, not 125.50).
- **Business Impact:** Any flow that trusts the reset response (tests, support tooling, the user) sees a balance that is not real. Undermines every balance-dependent assertion and the user's trust in their funds.
- **Evidence:** paired `reset` vs `GET /api/balance` responses, 3 consecutive runs.

## BUG-04 — UI header balance does not refresh after a bet

- **Severity:** High
- **Component:** Header / bet-slip balance display
- **Reproduction Steps:**
  1. Open the app; header shows Balance €120.00.
  2. Place a €10 bet; dismiss the receipt.
  3. Observe the header balance for several seconds; query `GET /api/balance`.
- **Expected vs Actual:**
  - **Expected:** after a successful bet the displayed balance drops by the stake (→ €110.00).
  - **Actual:** the server balance updates to `110`, but the UI header stays frozen at **€120.00** (observed stable for 5+ seconds, through receipt close). A manual reload is required to see the real balance.
- **Business Impact:** The user sees stale funds and can be misled into over-betting (compounding BUG-01), and loses confidence that the displayed balance is real.
- **Evidence:** server `GET /api/balance` = 110 while header read 120 across 10 polls.

## BUG-05 — Receipt lists the teams in reversed order

- **Severity:** Medium
- **Component:** Success receipt modal (`#modal-success-match`)
- **Reproduction Steps:** Place a bet on Manchester Utd (home) vs Chelsea (away); read the receipt match line.
- **Expected vs Actual:**
  - **Expected (Domain Context — home team listed first, carried through to the receipt):** "Manchester Utd vs Chelsea".
  - **Actual:** receipt shows **"Chelsea vs Manchester Utd"** (away vs home).
- **Business Impact:** Misrepresents which outcome was backed; for a Home bet the receipt reads as if the away team were home, which is confusing and dispute-prone.
- **Evidence:** `evidence/03-receipt-BUG-payout-and-team-order.png`.

## BUG-06 — `place-bet` responses report currency `USD` instead of `EUR`

- **Severity:** Medium
- **Component:** `POST /api/place-bet` response contract
- **Reproduction Steps:** Place any bet; inspect the response `currency` field. Compare with `GET /api/balance` and `POST /api/reset-balance`.
- **Expected vs Actual:**
  - **Expected (spec — EUR throughout):** `"currency":"EUR"`.
  - **Actual:** every `place-bet` response returns `"currency":"USD"`, while `balance` and `reset-balance` correctly return `"EUR"`.
- **Business Impact:** Inconsistent currency in a money API; a client trusting the field could display or reconcile the wrong currency.
- **Evidence:** `place-bet` body `{… "currency":"USD"}` vs `balance` body `{… "currency":"EUR"}`.

## BUG-07 — Payout is truncated instead of rounded

- **Severity:** Medium
- **Component:** Payout calculation
- **Reproduction Steps:** `POST /api/place-bet` `{matchId:"serie-a-juve-milan", selection:"AWAY", stake:12.5}` (odds 4.1).
- **Expected vs Actual:**
  - **Expected:** 12.5 × 4.1 = 51.2499… → **51.25** (round to 2 dp).
  - **Actual:** API returns `payout: 51.24` (truncated).
- **Business Impact:** Systematic €0.01 under-payment on bets whose payout has a third-decimal ≥5; small per bet, but it is incorrect money math and accumulates.
- **Evidence:** `place-bet` response `payout:51.24`.

## BUG-08 — `GET /api/place-bet` returns `200 {}` instead of `405`

- **Severity:** Medium
- **Component:** `/api/place-bet` method handling
- **Reproduction Steps:** `GET /api/place-bet` (valid id) → `200 {}`; `PUT /api/place-bet` → `405 method_not_allowed`.
- **Expected vs Actual:**
  - **Expected (spec §4.3):** unsupported methods return `405`. `place-bet` is POST-only.
  - **Actual:** `GET` returns `200 {}` (misleading success); only the GET verb is mishandled (PUT/DELETE correctly 405).
- **Business Impact:** A misleading health signal; monitoring/probes `GET`-ing the endpoint see "OK", masking method-handling issues.

## BUG-09 — Malformed JSON body returns `500` instead of `400`

- **Severity:** Medium
- **Component:** `POST /api/place-bet` request parsing
- **Reproduction Steps:** `POST /api/place-bet` with body `{bad json` → **`500 internal_server_error`**. (A valid-JSON non-object like `[1,2,3]` correctly returns `400 invalid_request`; a quoted string returns `400 invalid_json`.)
- **Expected vs Actual:**
  - **Expected (spec §4.3 / Swagger):** malformed JSON → `400 invalid_json`.
  - **Actual:** truly-malformed JSON crashes to `500`. The server distinguishes other bad-body cases correctly, so only the unparseable case is mishandled.
- **Business Impact:** A client bug (bad serialization) surfaces as a server error, hiding the real cause and polluting server-error metrics/alerts.

---

## Correct behaviours confirmed (recorded for balance)

- Missing `x-user-id` → `401 missing_user_id`; valid issued id authenticates and returns real data.
- Stake validation taxonomy is correct: `invalid_stake_min` / `max` / `precision` / `type` all `422`.
- Selection/match validation: `invalid_selection`, `invalid_match`, `invalid_match_id` all `422`.
- Concurrency: two bets fired in parallel → one `200`, one `409 bet_in_progress` (correct guard).
- Extra request fields are ignored (`200`), per spec.
- `PUT`/`DELETE` on single-method routes correctly return `405`.

## Spec clarification (not a defect)

Minimum stake is stated inconsistently: Business Rules say **€1.00**, the Validation table (§4.1)
says **€1.01**, and the API message says "at least 1.00". Tests assert the API's own
contract (`≥ 1.00`). Worth resolving so the boundary has a single source of truth.
