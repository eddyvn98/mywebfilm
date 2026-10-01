# Cinema Security Deployment

This project is designed as a single-user personal web application. Production access should use HTTPS, Passkeys/WebAuthn, and a private origin behind Cloudflare Tunnel.

## Required production environment

Set these values before attaching the real domain:

```text
CINEMA_SECRET_KEY=<random secret of at least 32 bytes>
CINEMA_SECURE_COOKIES=1
CINEMA_ALLOWED_HOSTS=cinema.example.com
CINEMA_PUBLIC_URL=https://cinema.example.com
CINEMA_IDLE_LOCK_SECONDS=900
CINEMA_OTT_TTL_SECONDS=120
```

For a temporary Quick Tunnel, optionally add:

```text
CINEMA_ALLOWED_EMAIL=you@example.com
```

The helper passes this value to `cloudflared --allowed-mail`.

## Recommended Cloudflare layout

Use a Named Cloudflare Tunnel for the permanent domain. Keep the Cinema service bound to localhost when the tunnel runs on the same machine:

```text
CINEMA_HOST=127.0.0.1
CINEMA_PORT=5000
```

Recommended path:

```text
Internet
  -> Cloudflare Access
  -> Named Cloudflare Tunnel
  -> http://127.0.0.1:5000
  -> Cinema Passkey
```

Cloudflare Access should allow only the owner's identity/email. Cinema Passkey remains the application authentication layer.

## Authentication model

- Existing Passkey: login directly; no QR bootstrap is needed.
- New device: create a short-lived one-time registration QR from Security -> Add device.
- Registration bootstrap token expires quickly and is consumed after successful registration.
- WebAuthn requires user verification.
- Authentication challenges are one-time and expire after 120 seconds.
- The application auto-locks after 15 minutes of inactivity.
- Continuous media playback counts as activity; background polling does not.
- Lock keeps the authenticated session so a Passkey can unlock it.
- Logout clears the session entirely.

## Cookie and browser protections

Production HTTPS should use `CINEMA_SECURE_COOKIES=1`.

The app also sends:
- `HttpOnly` session cookies
- `SameSite=Lax`
- HSTS on HTTPS
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- restrictive Permissions Policy
- no-store caching for authentication pages and APIs

## Device loss

Open Security -> Trusted devices and revoke the old device. The current device cannot revoke itself and the last remaining Passkey cannot be removed through the UI to reduce accidental lockout risk.

## Public repository warning

Runtime secrets and credentials are ignored by Git, but this repository should still be private if its generated HTML, metadata, or project history is personal. Repository visibility is an account-level GitHub setting and is not controlled by the application.
