# Authentication API

The API uses short-lived JWT access tokens and rotating refresh tokens. It uses Django's built-in `User` model; no custom user model or user profile fields are needed for the current MVP.

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/registration/` | Create an account with `email`, `password1`, and `password2`; the server generates a unique username |
| POST | `/api/auth/login/` | Sign in with `email` and `password` |
| POST | `/api/auth/logout/` | Blacklist a refresh token; send it as `refresh` in the request body |
| POST | `/api/auth/token/refresh/` | Rotate a refresh token |
| GET | `/api/auth/user/` | Get the current user's profile |
| POST | `/api/auth/google/` | Sign in with a Google authorization `code` or `access_token` |

For authenticated endpoints, send `Authorization: Bearer <access-token>`. Signup, password login, and social login return JWTs in the response body; the extension should store them in extension-only storage and send the access token as a bearer token. Refresh tokens are rotated and blacklisted after rotation.

## Local setup

Copy `.env.example` to `.env`, set the Django/database/provider values, and set `TABBOARD_EXTENSION_ID` to the installed extension's ID. Settings add its exact `chrome-extension://<extension-id>` origin to CORS; `CORS_ALLOWED_ORIGINS` is for any additional origins. Do not use `*` in production. Since auth uses bearer tokens rather than cookies, cross-origin credentials are disabled and the API does not depend on session cookies or CSRF tokens.

For Supabase PostgreSQL, set `DB_HOST`, `DB_PORT`, and `DB_USER` to the values from the dashboard's **Connect** panel. If direct connectivity is unavailable on an IPv4-only network, use the session or transaction pooler connection details. `DB_SSLMODE` defaults to `require`.

For Google Chrome extensions, a client ID without a secret is expected for a public client. Configure that client ID in the extension manifest and use `chrome.identity.getAuthToken()` to obtain a Google access token. Send it to `POST /api/auth/google/` as `{"access_token": "..."}`; django-allauth validates it with Google before the API issues its own JWTs. Do not put a client secret in the extension. This access-token flow does not require a callback URL.

The API also supports authorization-code exchange for confidential OAuth clients. That flow requires a client secret and the exact callback URL configured with the provider. Chrome's `chrome.identity.getRedirectURL()` is typically `https://<extension-id>.chromiumapp.org/`, distinct from the extension's `chrome-extension://` CORS origin. Generate and verify a random OAuth `state` in the extension before forwarding any authorization response.

Then apply migrations and start Django:

```sh
python manage.py migrate
python manage.py runserver
```

Google sign-in requires a Google OAuth application. Put its client ID in `.env`; a `SocialApp` configured in Django admin is also supported. The client secret is optional for the Chrome extension access-token flow.

The social endpoints validate provider credentials server-side through django-allauth. Do not send provider client secrets from the extension.

Email verification is disabled for the initial signup flow. Configure a production email backend and enable verification before allowing public production signup.
