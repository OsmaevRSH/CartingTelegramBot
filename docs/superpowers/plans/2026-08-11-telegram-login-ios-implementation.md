# Telegram Login iOS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the iOS pairing-code flow with browser-based Telegram Login, returning an opaque one-time code that the app redeems with PKCE for the existing session tokens.

**Architecture:** iOS creates state and a PKCE verifier/challenge, starts a server transaction, and opens the returned HTTPS login page in `ASWebAuthenticationSession`. The server login page sends Telegram's signed payload and state to a server callback; only the server validates it, creates a one-time code, and redirects to the fixed `carting://auth/callback`. iOS verifies callback state and exchanges code plus verifier; it never receives Telegram identity fields.

**Tech Stack:** Python, FastAPI, SQLite, Telegram Login Widget HMAC; Swift, AuthenticationServices, CryptoKit, URLSession, XCTest/XCUITest.

## Global Constraints

- Use exactly `POST /api/mobile/auth/telegram/start`, `GET /api/mobile/auth/telegram/login?state=...`, `POST /api/mobile/auth/telegram/callback`, and `POST /api/mobile/auth/telegram/exchange`.
- Start accepts only `code_challenge_method: "S256"`; state and code are server-generated, high-entropy, opaque, single-use values.
- Transactions last 10 minutes; authorization codes last 60 seconds. Store hashes, never raw state, code, verifier, bot token, refresh token, or Telegram payload in the database or logs.
- Telegram HMAC verification and user mapping run only on the server. iOS never reads or submits Telegram signed fields, credentials, or bot token.
- The sole redirect target is `carting://auth/callback`; production login requests require HTTPS and no caller supplies a redirect URL.
- Preserve `TokenResponse`, 15-minute access JWTs, refresh-session creation/rotation, logout, bearer middleware, protected stats, Keychain format, and existing user/statistics identity.
- Remove pairing completely: bot `/ios` command/menu/text, `mobile_pairing_codes`, pairing helpers and endpoint, iOS pairing API/UI/tests/fixtures/docs. Old clients cannot create a new session.
- Return `401` with non-sensitive Russian messages for malformed, unknown, expired, reused, state-mismatched, or PKCE-invalid authentication requests.

### Task 1: Add transaction/code persistence and server-side contract tests

**Files:**
- Modify: `core/database/db.py`
- Modify: `tests/test_mobile_auth.py`
- Modify: `tests/test_mobile_stats.py`

**Interfaces:**
- Produces database helpers for creating/finding a 10-minute login transaction and atomically consuming a 60-second authorization code against state and PKCE verifier.

- [ ] **Step 1: Write failing database/auth tests.** Cover unique state, rejected non-S256 or malformed challenge, 10-minute transaction expiry, 60-second code expiry, one-time code consumption, state mismatch, verifier mismatch, and assertions that stored rows contain hashes rather than raw state/code/verifier.
- [ ] **Step 2: Run `pytest -q tests/test_mobile_auth.py tests/test_mobile_stats.py` and confirm the new tests fail.**
- [ ] **Step 3: Replace `mobile_pairing_codes` initialization with `mobile_telegram_login_transactions` (hashed state and challenge, created/expiry/completion fields) and `mobile_telegram_authorization_codes` (hashed code, user id, transaction reference, created/expiry/consumed fields).** Preserve `mobile_refresh_sessions`, users, and statistics; opportunistically delete expired/consumed auth records during auth operations.
- [ ] **Step 4: Add narrowly scoped helpers that use cryptographic hashes and a SQLite transaction to create transactions, mark callback completion, issue codes, and atomically consume an unexpired code only when its transaction state and S256 verifier match.**
- [ ] **Step 5: Re-run the focused tests and commit `feat(auth): persist Telegram login transactions`.**

### Task 2: Implement server browser login, Telegram callback validation, and exchange

**Files:**
- Modify: `api/routes/auth.py`
- Modify: `core/config/config.py`
- Modify: `core/auth/tokens.py`
- Modify: `tests/test_mobile_auth.py`
- Modify: `env.example`

**Interfaces:**
- Consumes the Task 1 persistence helpers.
- Produces `POST /telegram/start -> { authorization_url, state, expires_in }`, browser `GET /telegram/login`, server-only `POST /telegram/callback`, and `POST /telegram/exchange -> TokenResponse`.

- [ ] **Step 1: Write failing route tests.** Test start response and URL, live-state-only login page, callback HMAC success, altered/missing hash, malformed/non-numeric Telegram ID, stale date and date over 60 seconds in the future, new/existing user behavior, missing Telegram fields not overwriting a stored profile, final opaque-code redirect, exchange success/reuse/state/verifier failures, and unchanged refresh/logout/stats behavior.
- [ ] **Step 2: Run `pytest -q tests/test_mobile_auth.py tests/test_mobile_stats.py` and confirm failure.**
- [ ] **Step 3: Add configuration for the server bot token and fixed public HTTPS login origin; document only configuration variable names in `env.example`, never values.**
- [ ] **Step 4: Implement start: validate an S256 challenge, create state/transaction, and return a fixed-origin HTTPS `authorization_url` plus state and `expires_in`. Do not accept a redirect URL.**
- [ ] **Step 5: Implement login as a minimal HTML page for the configured Telegram bot. It takes only state, posts the successful Telegram widget payload to the server callback, and renders generic errors without putting payload, state, code, tokens, or verifier in HTML/logs/analytics.**
- [ ] **Step 6: Implement callback: first require a live transaction, then construct Telegram's sorted data-check string excluding `hash`, derive the HMAC secret from server config, compare in constant time, and enforce `auth_date` freshness. Map only the validated Telegram ID to the existing safe provisioning path; issue one opaque code and redirect only to `carting://auth/callback?code=...&state=...`.**
- [ ] **Step 7: Implement exchange: atomically consume the code, verify transaction state and PKCE S256 verifier, then reuse existing token functions to return `TokenResponse`. Ensure no access or refresh token enters the browser redirect.**
- [ ] **Step 8: Re-run focused tests, then commit `feat(auth): add browser Telegram Login flow`.**

### Task 3: Remove backend and bot pairing flow

**Files:**
- Modify: `bot/handlers/bot.py`
- Modify: `api/routes/auth.py`
- Modify: `core/database/db.py`
- Modify: `tests/test_mobile_auth.py`
- Modify: `tests/test_mobile_stats.py`
- Modify: `CLAUDE.md`
- Modify: `env.example`

**Interfaces:**
- Consumes the replacement `/api/mobile/auth/telegram/*` flow from Task 2.
- Produces no pairing command, pairing route, table, helper, docs, or user-reachable fallback.

- [ ] **Step 1: Add failing removal tests asserting `/ios`, `POST /api/mobile/auth/exchange`, `mobile_pairing_codes`, `create_pairing_code`, and `consume_pairing_code` are absent while refresh, logout, bearer access, and stats remain available.**
- [ ] **Step 2: Run the focused pytest command and confirm removal assertions fail.**
- [ ] **Step 3: Delete pairing command handling, menu registration, bot messages, pairing request model/route, and helpers; retain only the new Telegram endpoints and non-pairing auth lifecycle.**
- [ ] **Step 4: Replace pairing instructions in `CLAUDE.md` and `env.example` with login-domain, HTTPS, bot-token configuration, fixed callback, and deployment safety guidance.**
- [ ] **Step 5: Re-run focused tests and commit `refactor(telegram): remove pairing flow`.**

### Task 4: Implement iOS PKCE browser start, callback verification, and exchange

**Files:**
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/Core/API/APIEndpoint.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/Core/API/APIClient.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/Core/Auth/AuthService.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/CartingTests/AuthServiceTests.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/CartingTests/APIClientTests.swift`

**Interfaces:**
- Consumes `/telegram/start` and `/telegram/exchange`; stores only the existing `TokenResponse` through the existing Keychain token store.
- Produces an injectable auth coordinator with `continueWithTelegram()` that completes only after callback state verification and code/verifier exchange.

- [ ] **Step 1: Write failing XCTest cases for 43--128-character URL-safe verifier generation, SHA-256 base64url challenge, encoded start/exchange bodies, successful start -> system session -> callback -> exchange -> Keychain save, state mismatch, malformed callback URL, exchange rejection, and cancellation. Assert tests never model Telegram payload fields.**
- [ ] **Step 2: Run the focused CartingTests target and confirm failure.**
- [ ] **Step 3: Add API request/response models and endpoints for start (`code_challenge`, `code_challenge_method`) and exchange (`code`, `state`, `code_verifier`); remove the pairing exchange request. Keep diagnostics secret-free.**
- [ ] **Step 4: Implement the auth coordinator: generate state and PKCE before start; open the returned HTTPS URL with `ASWebAuthenticationSession` and callback scheme `carting`; require host/path `auth/callback`, exact state equality, and nonempty opaque code; then exchange code with the original verifier and persist the established token session.**
- [ ] **Step 5: Treat cancellation, malformed callback, mismatched state, and server rejection as unauthenticated retryable errors; never parse Telegram login payloads. Re-run focused unit tests and commit `feat(ios): add PKCE Telegram Login authentication`.**

### Task 5: Replace iOS pairing UI and verify release behavior

**Files:**
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/Features/Auth/PairingView.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/Features/Auth/PairingViewModel.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/App/RootView.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/App/CartingApp.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting/Info.plist`
- Modify: `/Users/ltheresi/Documents/carting_ios/Carting.xcodeproj/project.pbxproj`
- Modify: `/Users/ltheresi/Documents/carting_ios/CartingTests/PairingViewModelTests.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/CartingUITests/PairingFlowUITests.swift`
- Modify: `/Users/ltheresi/Documents/carting_ios/README.md`

- [ ] **Step 1: Write failing view-model/UI tests for one accessible `Continue with Telegram` action, progress, retryable failure, and unauthenticated state after cancellation/no completed login. Remove code-entry assumptions and fixtures.**
- [ ] **Step 2: Run focused unit/UI tests and confirm failure.**
- [ ] **Step 3: Replace pairing input/submit copy and state with the one primary action wired to the Task 4 coordinator. Keep cancellation and all errors retryable; remove code-entry UI and persistence assumptions.**
- [ ] **Step 4: Register exactly the `carting` URL scheme in `Info.plist`; update app dependency wiring and Xcode project references for renamed/removed test assets as needed.**
- [ ] **Step 5: Update `README.md` with BotFather domain `carting.ltheresi.com`, production HTTPS and bot-token prerequisites, database backup/migration order, non-production end-to-end test, old-build cutoff, and the separate outbound-bot-network caveat.**
- [ ] **Step 6: Run focused tests plus the full unit target. On a simulator, verify the system login session launches and an incomplete Telegram login returns the app to unauthenticated retry state. Commit `feat(ios): replace pairing UI with Telegram Login`.**

## Final verification

- Confirm server callback—not iOS—receives and validates Telegram signed payloads, and the browser redirect contains only opaque `code` and `state`.
- Confirm raw state, authorization code, verifier, refresh token, bot token, and Telegram payload are absent from persisted rows, logs, analytics, errors, and documentation examples.
- Confirm all specified pairing-only code and data paths are absent, while refresh rotation, logout, bearer access, and stats stay green.
- Before production rollout: configure BotFather with `carting.ltheresi.com`, deploy HTTPS and bot token, back up SQLite, deploy migration/backend, check health/start, ship the iOS build, and complete end-to-end sign-in using a non-production account.
