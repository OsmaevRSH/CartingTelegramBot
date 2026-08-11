# Telegram Login for native iOS

## Goal

Replace the iOS pairing-code flow completely with a familiar Telegram sign-in
flow. A person authorizes with Telegram in a system browser session and returns
to the native Carting app already signed in. Existing users, statistics, and
leaderboard identity remain keyed by the same Telegram user ID.

The pairing mechanism is removed rather than retained as a fallback: there is
no `/ios` bot command, no code shown by the bot, and no code-entry screen or
pairing API in the app.

## Selected approach

The iOS client uses `ASWebAuthenticationSession` to open an HTTPS Carting login
page. That page hosts Telegram Login for the configured Carting bot. Telegram
posts or redirects the signed user payload to the Carting backend; the backend
validates it and redirects the system session to `carting://auth/callback` with
an opaque, one-time authorization code. The app redeems that code with PKCE for
the existing JWT access and refresh-token pair.

This is deliberately a browser-based Telegram authorization, not a custom
Telegram deep link and not a bot chat interaction. It is supported when the
Telegram app is absent because the system web session can authenticate through
Telegram's web UI.

## Components and responsibilities

### iOS app

- The unauthenticated screen has one primary action: **Continue with
  Telegram**. It replaces the pairing-code text field and submit action.
- Before opening the browser session, the app generates a cryptographically
  random PKCE verifier (43--128 URL-safe characters), derives its SHA-256
  base64url challenge, and calls the start endpoint.
- The app opens the returned HTTPS authorization URL with
  `ASWebAuthenticationSession`, using `carting` as the callback URL scheme.
- When the session returns `carting://auth/callback?code=...&state=...`, the
  app verifies the returned state equals the one it created, then sends the
  code and original verifier to the exchange endpoint.
- The app never reads Telegram credentials or Telegram Login payload fields.
  It stores only the existing access/refresh session in Keychain. Cancellation,
  a malformed callback, or an exchange rejection leaves it unauthenticated and
  presents a retryable error.

### Backend API and login page

- `POST /api/mobile/auth/telegram/start` accepts the PKCE
  `code_challenge` and `code_challenge_method` (`S256` only). It creates an
  unguessable state and login transaction, stores only the state and challenge
  hashes, and returns `{ authorization_url, state, expires_in }`.
- `GET /api/mobile/auth/telegram/login?state=...` serves a minimal HTTPS page which
  initializes Telegram Login for the configured bot and sends the successful
  Telegram payload to the callback endpoint. The page must not expose the bot
  token, JWTs, refresh tokens, or the PKCE verifier.
- `POST /api/mobile/auth/telegram/callback` receives the Telegram Login
  payload and state. It validates the transaction first, then validates
  Telegram's `hash` according to Telegram Login: construct the sorted data
  check string without `hash`, derive the secret from the bot token, compare
  the HMAC in constant time, and require a fresh `auth_date`.
- A valid payload is mapped to the Carting user by Telegram user ID. If that ID
  does not yet exist, the backend creates the user through the existing safe
  user-provisioning logic, using only the minimum Telegram fields needed for a
  valid profile. If it already exists, missing or empty Telegram fields must
  not overwrite the stored profile. The backend never trusts a user ID supplied
  by the iOS app. The callback creates an opaque one-time authorization code and redirects to
  `carting://auth/callback?code=...&state=...`.
- `POST /api/mobile/auth/telegram/exchange` accepts `code`, `state`, and
  `code_verifier`. It atomically consumes the authorization code, checks the
  transaction state and PKCE S256 challenge, then issues the current 15-minute
  access JWT and a newly created refresh session using the existing token code.
- Existing `POST /api/mobile/auth/refresh` and `/logout`, bearer middleware,
  protected mobile stats APIs, JWT claims, Keychain session format, and refresh
  rotation remain unchanged.

## Persisted state and expiry

Add two narrowly scoped database tables:

| Table | Stored values | Lifetime / use |
| --- | --- | --- |
| `mobile_telegram_login_transactions` | hashes of state and PKCE challenge, creation/expiry timestamps, completion status | 10 minutes; one browser attempt |
| `mobile_telegram_authorization_codes` | hash of opaque code, user ID, transaction reference, creation/expiry/consumption timestamps | 60 seconds; one exchange only |

Raw state, authorization codes, PKCE verifiers, bot token, and refresh token
values are never stored in the database or logs. Expired and consumed records
may be removed opportunistically during auth operations. Existing
`mobile_refresh_sessions` is preserved. `mobile_pairing_codes` and its helper
functions are removed in the same migration; this does not touch user,
statistics, or refresh-session data.

## Security and error contract

- The backend accepts only HTTPS login-page requests in production and has one
  fixed callback scheme/host: `carting://auth/callback`. It does not accept a
  caller-provided redirect URL.
- Every state and authorization code is high-entropy, server generated,
  single-use, and expires as specified above. State mismatch, unknown/expired
  transactions, reused codes, an invalid verifier, and malformed requests all
  return `401` with a non-sensitive Russian error message.
- Telegram payload validation rejects a missing/invalid hash, a non-numeric
  Telegram ID, and `auth_date` older than 10 minutes or more than 60 seconds in
  the future. The bot token is read only from server configuration.
- The callback page reports login failures without echoing Telegram payload,
  state, code, tokens, or verifier into HTML, URLs (other than the final opaque
  code/state callback), analytics, or logs.
- The exchange response is the current `TokenResponse`; no access or refresh
  token appears in the browser redirect.

## Removal scope

Remove all pairing-only functionality together:

- `/ios` command, its handler, command-menu registration, and bot text.
- `mobile_pairing_codes`, `create_pairing_code`, `consume_pairing_code`, and
  the `POST /api/mobile/auth/exchange` pairing endpoint.
- Pairing-code request models, tests, documentation, iOS API methods, UI,
  persistence assumptions, and test fixtures.

The old iOS build will no longer be able to sign in after the server rollout;
users must install a build containing Telegram Login. Existing signed-in old
installations can continue using a valid access/refresh session until its
normal expiry or logout, but cannot create a new session.

## Verification

Backend tests cover:

- correct HMAC validation; altered data, missing hash, stale/future auth date,
  and malformed Telegram ID rejection;
- start rejects non-S256 or invalid challenges; state is unique and expires;
- callback accepts only a live transaction and creates one opaque code;
- exchange succeeds only with matching state and verifier and cannot be reused;
- no raw state, authorization code, verifier, or refresh token is persisted;
- existing refresh rotation, logout, bearer access, and mobile stats tests stay
  green;
- `/ios`, pairing endpoints, and pairing table/helpers are absent.

iOS tests cover generating a PKCE challenge, the start request, successful
callback/exchange and Keychain save, callback state mismatch, malformed URL,
server rejection, and user cancellation. A simulator smoke test confirms the
system login session launches and the app returns to its unauthenticated retry
state if no Telegram login is completed.

## Deployment and release

1. In BotFather, configure the Telegram Login domain exactly as
   `carting.ltheresi.com` for the existing Carting bot before enabling the new
   login page.
2. Configure the production API with the bot token and ensure
   `carting.ltheresi.com` serves valid HTTPS for the login page and callback.
3. Back up the production SQLite database, deploy the backend migration and
   verify health plus the start endpoint, then deploy the new signed iOS build.
4. Test an end-to-end sign-in with a non-production test account before
   communicating the cutoff of old builds.

Telegram Login does not require the server bot process to send a message for
the iOS sign-in itself. The separate outbound-network problem that prevents
the bot from contacting Telegram still has to be fixed for other bot features.
