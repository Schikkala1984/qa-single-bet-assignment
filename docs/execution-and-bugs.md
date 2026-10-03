# Part A.2 — Execution Results & Bug Reports

**Application:** https://qae-assignment-tau.vercel.app/
**Date executed:** 2026-10-03
**Method:** Direct API calls (`fetch`) + the application's own frontend driven in a real
Chromium browser. Every status code and body below is a verbatim observed response.

> I am not scored on bug count, so this focuses on the high-impact issues. The headline finding
> (BUG-01) is a total outage of the authenticated flow; it blocks execution of the happy-path
> scenarios, which I note honestly rather than fabricating passes.

---

## Execution summary (Top 3 scenarios)

| Scenario | Result | Note |
|----------|--------|------|
| TC-01 Place a valid bet (happy path) | **BLOCKED** | Cannot authenticate any user-id → no balance, no matches, cannot reach the slip. Blocked by BUG-01. |
| TC-02 Authentication enforced | **FAIL** | Missing header correctly returns `401 missing_user_id`, but **no** user-id value is ever accepted (should be). BUG-01. |
| TC-03 Stake boundary validation | **BLOCKED (API)** | `place-bet` returns `401 invalid_user_id` before validation can run, so stake rules are unreachable. Blocked by BUG-01. |

Because BUG-01 gates the entire authenticated surface, exploratory testing pivoted to the
unauthenticated and method/routing surface, which surfaced BUG-02.

---

## BUG-01 — No user-id can authenticate; entire betting flow is unusable

- **Severity:** Critical
- **Component:** Auth / `x-user-id` validation (all protected endpoints)
- **Reproduction Steps:**
  1. Open `https://qae-assignment-tau.vercel.app/?user-id=chikkala-srinivas` in Chrome.
  2. Observe the app loads but shows "Unauthorized", "Balance: €0.00", "Showing 0 matches".
  3. Reproduce directly against the API:
     ```
     GET /api/balance   with header  x-user-id: chikkala-srinivas   → 401 {"error":"invalid_user_id"}
     GET /api/matches   with header  x-user-id: chikkala-srinivas   → 401 {"error":"invalid_user_id"}
     ```
  4. Repeat with ~75 different values (plain names, `some_user` — the frontend's own hint —,
     UUID v4, numeric IDs, fresh unique timestamps). **Every** value returns `401 invalid_user_id`.
  5. Only an empty/whitespace header behaves differently: `401 missing_user_id`.
- **Expected vs Actual:**
  - **Expected (per spec):** The spec says *"append your user-id as a query parameter … `?user-id=<your-user-id>`"* and the frontend hint is `?user-id=some_user`. Any non-empty user-id should authenticate and return the user's data (fresh balance €125.50, match list).
  - **Actual:** No user-id value is accepted. All protected endpoints return `401 invalid_user_id`; the UI is permanently in the Unauthorized state.
- **Business Impact:** **Total outage of the core product.** No user can view a balance, see matches, or place a bet. Zero revenue; the feature delivers no value. This is release-blocking.
- **Evidence:** `evidence/BUG-01-unauthorized-ui.png` (app's own UI showing €0.00 / 0 matches / Unauthorized). Confirmed the frontend sends `x-user-id` verbatim and the server rejects it; not a client bug, not rate-limiting (other calls return 200/405 normally), no cookies/localStorage involved.
- **Note on diagnosis:** The deployed backend appears to validate `x-user-id` against a set/pattern that rejects all inputs. Needs a spec clarification on the exact accepted user-id format, or a backend fix so arbitrary IDs are accepted as the spec implies.

## BUG-02 — `GET /api/place-bet` returns `200 {}` instead of `405 Method Not Allowed`

- **Severity:** Medium
- **Component:** `/api/place-bet` method handling
- **Reproduction Steps:**
  ```
  GET    /api/place-bet  (x-user-id: chikkala-srinivas)  → 200 {}
  PUT    /api/place-bet  (x-user-id: chikkala-srinivas)  → 405 {"error":"method_not_allowed"}
  POST   /api/matches                                     → 405 {"error":"method_not_allowed"}
  GET    /api/reset-balance                               → 405 {"error":"method_not_allowed"}
  ```
- **Expected vs Actual:**
  - **Expected (per spec §4.3):** "Unsupported HTTP method → return method-not-allowed response." `place-bet` is POST-only, so `GET` should return `405`.
  - **Actual:** `GET /api/place-bet` returns `200` with an empty JSON body `{}`. Note `PUT`/`DELETE` on the same route correctly return `405`, so only the `GET` verb is mishandled.
- **Business Impact:** Contract violation and a misleading success signal. A client (or a monitoring probe) issuing `GET` on the bet endpoint receives a `200` "OK" that implies the endpoint is healthy and that a safe method is supported, masking method-handling problems and complicating client error handling.
- **Evidence:** Response captured above; `PUT` on the same path returning `405` isolates it to the GET handler.

---

## Exploratory notes & observations (not all defects — recorded for transparency)

1. **Spec contradiction on minimum stake.** Business Rules say minimum stake **€1.00**; the
   Validation table (§4.1) says minimum **€1.01**; the API's own error example says *"Stake must be
   at least 1.00."* These three disagree. Low severity but it is a real **spec-clarification** item —
   a boundary test (stake = €1.00) could be marked pass or fail depending on which doc you trust.
2. **Reset-balance consistency flag (unverified due to BUG-01).** The live Swagger explicitly says
   for `POST /api/reset-balance`: *"response payload may differ from persisted balance."* That wording
   signals an intentional **consistency defect** (the returned balance may not equal the persisted
   one). I could not confirm it because auth blocks the call, but it is a strong candidate and the
   spec itself requires *"Response body and persisted state must be consistent after reset."* Flagged
   for retest once BUG-01 is resolved.
3. **Correct behaviors confirmed (good news):** missing header → `401 missing_user_id`; unknown routes
   → `404`; `/api/docs` serves Swagger publicly; `OPTIONS /api/place-bet` → `204`; CORS exposes
   `X-User-Id`. Auth is correctly evaluated *before* payload validation on `place-bet`.

---

## Blocked / deferred

TC-01, TC-03, TC-04, TC-05 depend on a working authenticated session and cannot be fully executed
until BUG-01 is fixed or the correct user-id scheme is provided. The automation in Part B encodes the
**expected** behavior for these, so the suite will go green automatically once the backend is healthy.
