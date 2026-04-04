# WebAuthn + Tunnel One-Time Token Gate

Tags: `security`, `webauthn`, `auth`, `cloudflare`

## Concept
Use WebAuthn for strong login and add a one-time tunnel token for remote registration/login endpoints.

## When to use
- Local-first app exposed via temporary tunnel
- You need phishing-resistant auth

## When NOT to use
- Multi-user IAM systems needing RBAC/SSO
- Apps requiring persistent distributed auth state

## Example
```python
is_local = request.remote_addr in ['127.0.0.1', '::1']
if not is_local and token_req != CURRENT_OTT:
    return jsonify({"status": "err"}), 403
```

