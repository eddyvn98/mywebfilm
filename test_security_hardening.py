import time
from unittest.mock import patch

import pytest

from webfilm import app
import routes.api_auth as api_auth


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def authenticate(client):
    with client.session_transaction() as sess:
        sess['authenticated'] = True


def test_config_api_never_returns_server_secrets(client):
    authenticate(client)
    fake = {
        'video_dirs': ['D:/Media'],
        'gemini_api_key': 'secret-key',
        'scrapper_cookies': 'secret-cookie',
        'auto_convert_ts': True,
    }
    with patch('routes.api_config.cfg.load_config', return_value=fake):
        payload = client.get('/api/config').get_json()

    assert 'gemini_api_key' not in payload
    assert 'scrapper_cookies' not in payload
    assert payload['gemini_configured'] is True
    assert payload['scrapper_cookies_configured'] is True


def test_queue_rejects_paths_outside_library(client):
    authenticate(client)
    with patch('routes.api_process.check_path_safe', return_value=False):
        resp = client.post('/api/process/queue', json={'paths': ['C:/Windows/win.ini']})
    assert resp.status_code == 403


def test_ai_inject_rejects_paths_outside_library(client):
    authenticate(client)
    with patch('utils.check_path_safe', return_value=False):
        resp = client.post(
            '/api/ai/inject',
            json={'filename': 'x.mp4', 'path': 'C:/Windows/win.ini', 'metadata': {}},
        )
    assert resp.status_code == 403


def test_expired_token_is_rejected_for_remote_login_options(client):
    api_auth.CURRENT_OTT = 'a' * 32
    api_auth.CURRENT_OTT_EXPIRES_AT = time.time() - 1
    resp = client.get(
        '/api/auth/login/options?token=' + ('a' * 32),
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 403


def test_valid_token_is_consumed_after_remote_login(client, monkeypatch):
    api_auth.CURRENT_OTT = 'b' * 32
    api_auth.CURRENT_OTT_EXPIRES_AT = time.time() + 300
    monkeypatch.setattr(api_auth, 'get_origin', lambda: 'https://example.test')
    monkeypatch.setattr(api_auth.security_manager, 'verify_authentication', lambda *args, **kwargs: True)

    resp = client.post(
        '/api/auth/login/verify?token=' + ('b' * 32),
        json={},
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 200
    assert api_auth.CURRENT_OTT is None
    assert api_auth.CURRENT_OTT_EXPIRES_AT == 0.0
