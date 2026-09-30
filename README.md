# MyWebFilm

Local-first Flask media library manager for Windows with streaming, metadata management, WebAuthn login, FFmpeg processing, and automatic sorting.

## Requirements

- Python 3.12 recommended.
- FFmpeg and FFprobe available on PATH.
- Windows is required for desktop-launch features such as Explorer/MPC-HC; the core test suite is platform-neutral.

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python webfilm.py
```

Open `http://localhost:5000`.

## Runtime data

Runtime authentication state and generated secrets live under `data/` by default and must not be committed. Set `CINEMA_DATA_DIR` to move that directory.

`CINEMA_SECRET_KEY` can be supplied explicitly. If omitted, the app creates a random persistent key in `data/flask_secret.key`.

For HTTPS/tunnel use, set `CINEMA_SECURE_COOKIES=1`.

## Highlight behavior

Highlight processing intentionally replaces storage usage by deleting the original source after the generated highlight passes media validation. If FFmpeg or FFprobe validation fails, the source is retained.

## Tests

```bash
pytest -q
```

GitHub Actions runs Python compilation, pytest with coverage, security/data-safety regressions, and JavaScript syntax checks for pushes and pull requests.

## Production hardening

See `docs/PRODUCTION_HARDENING_PLAN.md`.
