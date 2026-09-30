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


def test_cross_origin_state_change_is_blocked(client):
    authenticate(client)
    resp = client.post(
        '/api/config/update',
        json={'auto_convert_ts': True},
        headers={'Origin': 'https://evil.example'},
    )
    assert resp.status_code == 403


def test_explorer_rejects_unsafe_path_before_launch(client):
    authenticate(client)
    with patch('routes.api_fs.os.path.exists', return_value=True), \
         patch('routes.api_fs.check_path_safe', return_value=False), \
         patch('routes.api_fs.subprocess.run') as run:
        resp = client.post('/api/explorer', json={'path': 'C:/Windows/win.ini'})
    assert resp.status_code == 403
    run.assert_not_called()


def test_path_guard_does_not_mutate_video_dirs(monkeypatch, tmp_path):
    import utils
    import config_manager as cfg

    allowed = tmp_path / 'allowed'
    allowed.mkdir()
    config = {'video_dirs': [str(allowed)]}
    monkeypatch.setattr(cfg, 'load_config', lambda: config)

    assert utils.check_path_safe(str(allowed / 'movie.mp4')) is True
    assert config['video_dirs'] == [str(allowed)]


def test_path_guard_resolves_symlink_escape(monkeypatch, tmp_path):
    import utils
    import config_manager as cfg

    allowed = tmp_path / 'allowed'
    outside = tmp_path / 'outside'
    allowed.mkdir()
    outside.mkdir()
    link = allowed / 'escape'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('symlinks unavailable on this platform')

    config = {'video_dirs': [str(allowed)]}
    monkeypatch.setattr(cfg, 'load_config', lambda: config)
    assert utils.check_path_safe(str(link / 'secret.txt')) is False


def test_config_update_response_never_returns_server_secrets(client):
    authenticate(client)
    fake = {
        'video_dirs': ['D:/Media'],
        'gemini_api_key': 'secret-key',
        'scrapper_cookies': 'secret-cookie',
        'auto_convert_ts': True,
    }
    with patch('routes.api_config.cfg.load_config', return_value=fake), \
         patch('routes.api_config.cfg.save_config'):
        payload = client.post(
            '/api/config/update',
            json={'auto_convert_ts': False},
        ).get_json()

    assert payload['status'] == 'ok'
    assert 'gemini_api_key' not in payload['config']
    assert 'scrapper_cookies' not in payload['config']
    assert payload['config']['gemini_configured'] is True
    assert payload['config']['scrapper_cookies_configured'] is True


def test_valid_ott_does_not_bypass_general_api(client):
    api_auth.CURRENT_OTT = 'c' * 32
    api_auth.CURRENT_OTT_EXPIRES_AT = time.time() + 300
    resp = client.get(
        '/api/videos?token=' + ('c' * 32),
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 401


def test_valid_ott_does_not_bypass_media_api(client):
    api_auth.CURRENT_OTT = 'd' * 32
    api_auth.CURRENT_OTT_EXPIRES_AT = time.time() + 300
    resp = client.get(
        '/api/stream?path=C:/Windows/win.ini&token=' + ('d' * 32),
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 401


def test_valid_ott_can_bootstrap_remote_registration_page(client):
    api_auth.CURRENT_OTT = 'e' * 32
    api_auth.CURRENT_OTT_EXPIRES_AT = time.time() + 300
    resp = client.get(
        '/register_security?token=' + ('e' * 32),
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 200


def test_project_static_is_not_a_media_root_by_default(monkeypatch):
    import os
    import utils
    import config_manager as cfg

    monkeypatch.setattr(cfg, 'load_config', lambda: {'video_dirs': []})
    project_static_file = os.path.join(os.path.dirname(utils.__file__), 'static', 'img', 'actors', 'x.jpg')

    assert utils.check_path_safe(project_static_file) is False
    assert utils.check_path_safe(project_static_file, allow_project_assets=True) is True
