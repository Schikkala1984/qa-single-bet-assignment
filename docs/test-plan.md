# Part A.1 — Test Plan: Single Bet Placement

**Feature:** Single Bet Placement (desktop web, football, pre-match, single bet only)
**Application under test:** https://qae-assignment-tau.vercel.app/?user-id=&lt;user-id&gt;
**Author:** Chikkala Srinivas
**Reference:** Single Bet Placement Feature Specification + live `/api/docs` OpenAPI contract

---

## Strategy & risk model

The spec defines a money-handling flow. The risks that actually hurt the user or the
business are, in order: (1) you cannot bet at all, (2) you are charged the wrong amount or
charged twice, (3) the receipt lies about what you placed, (4) validation lets a bad bet
through or blocks a good one. My scenario selection is weighted toward those risks rather
than toward exhaustive field-by-field coverage. "A focused submission with clear rationale
scores higher than a large one" — so each scenario below names the specific risk it buys down.

I deliberately split coverage across three layers:
- **UI E2E** for the journeys a user actually performs (selection → stake → place → receipt).
- **API** for validation and business-rule enforcement, where testing through the UI is slow,
  flaky, and often *cannot* reach the case (e.g. forged `selection`, precision, 409 concurrency).
- **Contract/consistency** for the money math and the reset state.

Priorities use: **Critical** (blocks release / money-loss), **High** (core rule, high
exposure), **Medium** (important but lower blast radius), **Low** (polish).

---

## Scenario summary

| ID | Title | Priority | Layer | Risk bucket |
|----|-------|----------|-------|-------------|
| TC-01 | Place a valid single bet — happy path, balance + receipt | Critical | UI E2E | Can't bet / correctness |
| TC-02 | Authentication required for all data + actions | Critical | API | Access control / outage |
| TC-03 | Stake boundary validation (min/max/precision) | High | API | Money correctness |
| TC-04 | Insufficient balance is rejected | High | API + UI | Over-spend protection |
| TC-05 | Receipt values match the selection & odds shown | High | UI E2E | Receipt integrity |
| TC-06 | Odds filter rejects an invalid min/max range | Medium | UI | Input robustness / feedback |

---

## TC-01 — Place a valid single bet (happy path)

- **Priority:** Critical
- **Risk Rationale:** This is the one journey the product exists to deliver. If it breaks, the
  product has zero value and revenue stops. It also exercises the money path end to end
  (balance before → stake deducted → correct payout → receipt), so it is the single highest-value
  check in the suite.
- **Preconditions:** Valid `user-id`, balance €125.50 (fresh / after reset), at least one upcoming match.
- **Steps:**
  1. Open `/?user-id=<valid-id>`.
  2. Note the header balance (expect €125.50).
  3. On the first match, click the home odds button (`1`).
  4. Confirm the bet slip shows that match, selection, and odds.
  5. Enter stake `10`.
  6. Verify the potential payout = `10 × odds` (e.g. 2.45 → €24.50).
  7. Click **Place Bet**; observe the loading (`Placing...`) state.
  8. Wait for resolution.
- **Expected Result:** Success receipt modal appears showing Bet ID, match, selection, stake €10,
  odds at placement, potential payout, timestamp. Balance decreases by exactly €10 (→ €115.50)
  in both header and slip. Closing the receipt returns to the main flow with no active selection.

## TC-02 — Authentication is enforced on every endpoint

- **Priority:** Critical
- **Risk Rationale:** `x-user-id` is the only thing standing between a request and a user's funds.
  Two failure modes are both catastrophic: auth too *loose* (one user acts as another / anonymous
  betting) or auth too *broken* (no valid user can be served — total outage). Testing this at the
  API layer is the only reliable way to assert status codes and error bodies precisely.
- **Preconditions:** None.
- **Steps:**
  1. `GET /api/balance` with **no** `x-user-id` header.
  2. `GET /api/balance` with a valid `x-user-id`.
  3. `GET /api/matches` with and without the header.
  4. `POST /api/place-bet` with a valid body but no header.
- **Expected Result:** Missing header → `401 missing_user_id`. A provided user-id → `200` with the
  user's data. Protected endpoints never return data without a valid user context.

## TC-03 — Stake boundary & precision validation (API)

- **Priority:** High
- **Risk Rationale:** Stake is the money input. Boundary bugs here mean under/over-charging or
  accepting malformed amounts. The boundaries (min, max, 2-dp precision, numeric type) are precisely
  the places defects hide, and the API is the authoritative enforcement layer ("UI + API" per spec).
- **Preconditions:** Valid user-id; a real `matchId` from `GET /api/matches`.
- **Steps (one `POST /api/place-bet` each, selection `HOME`):**
  1. stake `0.99` (below min) → expect reject.
  2. stake `1.00` (min boundary) → expect accept.
  3. stake `100.00` (max boundary) → expect accept (balance permitting).
  4. stake `100.01` (above max) → expect reject.
  5. stake `10.123` (3 decimals) → expect reject (`invalid_stake_precision`).
  6. stake `"abc"` (non-numeric) → expect reject (`invalid_stake_type`).
- **Expected Result:** Values inside [min, max] with ≤2 dp are accepted; others return `422` with the
  matching error code and a clear message (`invalid_stake_min` / `invalid_stake_max` /
  `invalid_stake_precision` / `invalid_stake_type`). *Note: spec states min €1.00 in Business Rules
  but €1.01 in the Validation table — see spec-clarification in the strategy note; test asserts the
  API's own contract (`≥ 1.00`).*

## TC-04 — Insufficient balance is rejected

- **Priority:** High
- **Risk Rationale:** A bet that exceeds available funds must never be accepted — otherwise the
  balance goes negative or the house pays out money the user never had. High business/financial impact.
- **Preconditions:** Known balance (reset → €125.50).
- **Steps:**
  1. Attempt a stake greater than the balance but ≤ €100 max is impossible (max < start balance),
     so: place bets to draw the balance below €10, then attempt a €10 bet; **or** at API level,
     stake a value within [1,100] that exceeds the *current* balance.
  2. Submit via UI and via `POST /api/place-bet`.
- **Expected Result:** Placement is rejected with an "Insufficient balance" message (UI) /
  `insufficient_balance` error (API). Balance is unchanged. No receipt is produced.

## TC-05 — Receipt matches the selection and odds shown pre-placement

- **Priority:** High
- **Risk Rationale:** The receipt is the user's proof of contract. If the receipt shows a different
  selection, odds, or payout than what was displayed when the user committed, it is a trust-and-dispute
  problem and a potential financial liability. Odds are "static for session", so the receipt odds must
  equal the odds shown on the match card.
- **Preconditions:** Valid user-id, fresh balance, ≥1 match.
- **Steps:**
  1. Record the match name, chosen selection, and the odds value displayed on the button.
  2. Enter a known stake; record the displayed potential payout.
  3. Place the bet; open the receipt.
  4. Compare receipt match / selection / odds / stake / payout against the recorded values.
- **Expected Result:** Every receipt field equals what was shown before placement; payout = stake × odds
  to 2 dp; home team is listed first (ordering convention).

## TC-06 — Odds filter rejects an invalid range

- **Priority:** Medium
- **Risk Rationale:** Filters are a secondary flow, but an invalid range (min > max) that is silently
  accepted or that crashes the list erodes trust and can hide matches. Lower blast radius than the
  money path, hence Medium. Good boundary/negative coverage of the filter contract.
- **Preconditions:** Match list loaded.
- **Steps:**
  1. Set odds filter min = `5.0`, max = `2.0` (min > max).
  2. Observe feedback and the match list.
  3. Correct to min = `2.0`, max = `5.0`.
- **Expected Result:** The invalid range is rejected with clear inline feedback and does not silently
  return an empty or wrong list; the corrected inclusive range filters matches correctly.

---

## Out of scope (consistent with the spec)

Live betting, accumulators/multi-bets, other sports, mobile UX, and odds that change mid-session.
These are explicitly out of scope and testing them would not reflect the feature contract.
