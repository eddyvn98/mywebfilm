import time
from unittest.mock import patch

import pytest

from webfilm import app
import routes.api_auth as api_auth
from test_helpers import authenticate_client, set_session_last_activity


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def authenticate(client):
    return authenticate_client(client)


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


def test_expired_token_is_rejected_for_remote_registration_options(client):
    api_auth.CURRENT_OTT = 'a' * 32
    api_auth.CURRENT_OTT_EXPIRES_AT = time.time() - 1
    resp = client.get(
        '/api/auth/register/options',
        headers={'X-Cinema-Bootstrap': 'a' * 32},
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 401


def test_valid_token_is_consumed_after_remote_registration(client, monkeypatch):
    monkeypatch.setenv('CINEMA_ALLOWED_HOSTS', 'example.test')
    api_auth.CURRENT_OTT = 'b' * 32
    api_auth.CURRENT_OTT_EXPIRES_AT = time.time() + 300
    monkeypatch.setattr(api_auth, 'get_origin', lambda: 'https://example.test')
    monkeypatch.setattr(
        api_auth.security_manager,
        'verify_registration',
        lambda *args, **kwargs: {'device_id': 'device-1', 'device_name': 'Phone'},
    )
    monkeypatch.setattr(
        api_auth.security_manager,
        'has_device',
        lambda _user_id, device_id: device_id == 'device-1',
    )

    resp = client.post(
        '/api/auth/register/verify',
        base_url='https://example.test',
        headers={
            'X-Cinema-Bootstrap': 'b' * 32,
            'Origin': 'https://example.test',
        },
        json={'credential': {}, 'challenge_id': 'challenge-1'},
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 200
    assert api_auth.CURRENT_OTT is None
    assert api_auth.CURRENT_OTT_EXPIRES_AT == 0.0

    status = client.get(
        '/api/auth/status',
        base_url='https://example.test',
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert status.status_code == 200
    assert status.get_json()['authenticated'] is True
    assert status.get_json()['locked'] is False


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


def test_registration_page_is_public_but_registration_api_is_gated(client):
    page = client.get(
        '/register_security',
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert page.status_code == 200

    options = client.get(
        '/api/auth/register/options',
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert options.status_code == 401


def test_remote_passkey_login_options_do_not_require_bootstrap(client, monkeypatch):
    monkeypatch.setattr(api_auth, 'get_origin', lambda: 'https://example.test')
    monkeypatch.setattr(
        api_auth.security_manager,
        'get_authentication_options',
        lambda *args, **kwargs: {'publicKey': {}, 'challenge_id': 'c1', 'expires_in': 120},
    )
    resp = client.get(
        '/api/auth/login/options',
        environ_overrides={'REMOTE_ADDR': '203.0.113.10'},
    )
    assert resp.status_code == 200
    assert resp.get_json()['challenge_id'] == 'c1'


def test_lock_blocks_application_apis(client):
    authenticate(client)
    with client.session_transaction() as sess:
        sess['last_activity'] = time.time()

    locked = client.post('/api/auth/lock')
    assert locked.status_code == 200

    resp = client.get('/api/videos')
    assert resp.status_code == 423
    assert resp.get_json()['code'] == 'LOCKED'


def test_security_headers_are_present(client):
    resp = client.get('/login')
    assert resp.headers['X-Content-Type-Options'] == 'nosniff'
    assert resp.headers['X-Frame-Options'] == 'DENY'
    assert resp.headers['Referrer-Policy'] == 'no-referrer'
    assert 'no-store' in resp.headers['Cache-Control']


def test_project_static_is_not_a_media_root_by_default(monkeypatch):
    import os
    import utils
    import config_manager as cfg

    monkeypatch.setattr(cfg, 'load_config', lambda: {'video_dirs': []})
    project_static_file = os.path.join(os.path.dirname(utils.__file__), 'static', 'img', 'actors', 'x.jpg')

    assert utils.check_path_safe(project_static_file) is False
    assert utils.check_path_safe(project_static_file, allow_project_assets=True) is True


def test_public_config_is_allowlisted_not_blacklisted(client):
    authenticate(client)
    fake = {
        'video_dirs': ['D:/Media'],
        'auto_convert_ts': True,
        'preferred_codec': 'h264',
        'future_secret': 'must-never-leak',
        'pin': '9999',
    }
    with patch('routes.api_config.cfg.load_config', return_value=fake):
        payload = client.get('/api/config').get_json()

    assert payload['video_dirs'] == ['D:/Media']
    assert payload['preferred_codec'] == 'h264'
    assert 'future_secret' not in payload
    assert 'pin' not in payload


def test_idle_session_auto_locks(client):
    session_id = authenticate(client)
    set_session_last_activity(
        session_id,
        time.time() - api_auth.IDLE_LOCK_SECONDS - 1,
    )

    resp = client.get('/api/videos')
    assert resp.status_code == 423
    assert resp.get_json()['code'] == 'LOCKED'


def test_activity_refreshes_idle_timer(client):
    session_id = authenticate(client)
    set_session_last_activity(session_id, time.time() - 10)

    resp = client.post('/api/auth/activity')
    assert resp.status_code == 200
    record = api_auth.runtime_db.get_security_session(session_id)
    assert time.time() - record['last_activity'] < 5


def test_cloudflare_loopback_is_not_direct_local_registration(client, monkeypatch):
    monkeypatch.setenv('CINEMA_ALLOWED_HOSTS', 'cinema.example.com')
    monkeypatch.setattr(
        api_auth.security_manager,
        'has_credentials',
        lambda _user_id: False,
    )
    resp = client.get(
        '/api/auth/register/options',
        base_url='https://cinema.example.com',
        headers={
            'CF-Connecting-IP': '203.0.113.77',
            'X-Forwarded-Proto': 'https',
            'X-Forwarded-Host': 'cinema.example.com',
        },
        environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
    )
    assert resp.status_code in {401, 403}


def test_cloudflare_loopback_cannot_sync_tunnel(client, monkeypatch):
    monkeypatch.setenv('CINEMA_ALLOWED_HOSTS', 'cinema.example.com')
    resp = client.post(
        '/api/auth/tunnel/sync',
        base_url='https://cinema.example.com',
        headers={
            'Origin': 'https://cinema.example.com',
            'CF-Connecting-IP': '203.0.113.77',
            'X-Forwarded-Proto': 'https',
            'X-Forwarded-Host': 'cinema.example.com',
        },
        json={
            'url': 'https://evil.trycloudflare.com',
            'token': 'a' * 48,
        },
        environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
    )
    assert resp.status_code == 403


def test_revoked_server_session_is_rejected(client):
    session_id = authenticate(client)
    api_auth.runtime_db.revoke_security_session(session_id, time.time())

    resp = client.get('/api/videos')
    assert resp.status_code == 401


def test_old_session_cannot_create_device_bootstrap(client, monkeypatch):
    authenticate_client(client, age_seconds=301)
    monkeypatch.setattr(
        'routes.api_config.TUNNEL_URL',
        'https://cinema.example.com',
    )
    resp = client.post('/api/auth/bootstrap')
    assert resp.status_code == 428
    assert resp.get_json()['code'] == 'REAUTH_REQUIRED'


def test_safe_path_not_in_catalog_cannot_be_streamed(client, tmp_path, monkeypatch):
    import config_manager as cfg

    media_root = tmp_path / "media"
    media_root.mkdir()
    unlisted = media_root / "secret.txt"
    unlisted.write_text("private", encoding="utf-8")
    monkeypatch.setattr(
        cfg,
        "load_config",
        lambda: {"video_dirs": [str(media_root)]},
    )
    authenticate(client)

    resp = client.get(
        "/api/stream",
        query_string={"path": str(unlisted)},
    )
    assert resp.status_code == 403


def test_remote_add_folder_cannot_expand_trusted_roots(client, tmp_path, monkeypatch):
    import config_manager as cfg

    trusted = tmp_path / "trusted"
    outside = tmp_path / "outside"
    trusted.mkdir()
    outside.mkdir()
    config = {"video_dirs": [str(trusted)]}
    monkeypatch.setattr(cfg, "load_config", lambda: config)
    monkeypatch.setattr(cfg, "save_config", lambda _value: None)
    monkeypatch.setenv("CINEMA_MEDIA_ROOTS", str(trusted))
    monkeypatch.setenv("CINEMA_ALLOWED_HOSTS", "cinema.example.com")
    authenticate(client)

    resp = client.post(
        "/api/add_folder",
        base_url="http://localhost",
        headers={
            "Origin": "https://cinema.example.com",
            "CF-Connecting-IP": "203.0.113.88",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "cinema.example.com",
        },
        json={"path": str(outside)},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert resp.status_code == 403
    assert config["video_dirs"] == [str(trusted)]


def test_queue_rejects_unknown_task_type(client):
    authenticate(client)
    resp = client.post(
        "/api/process/queue",
        json={"paths": ["anything"], "type": "shell"},
    )
    assert resp.status_code == 400


def test_logout_revokes_server_session_and_wipes_site_data(client):
    session_id = authenticate(client)
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert "cache" in resp.headers["Clear-Site-Data"]
    record = api_auth.runtime_db.get_security_session(session_id)
    assert record["revoked_at"] is not None

    denied = client.get("/api/videos")
    assert denied.status_code == 401


def test_csp_and_api_no_store_headers(client):
    login = client.get("/login")
    csp = login.headers["Content-Security-Policy"]
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp

    authenticate(client)
    api = client.get("/api/videos")
    assert "no-store" in api.headers["Cache-Control"]


def test_registration_challenge_store_is_bounded(monkeypatch):
    import security_service

    manager = security_service.security_manager
    with manager._challenge_lock:
        manager.challenges.clear()
        now = time.time()
        for index in range(security_service.MAX_ACTIVE_CHALLENGES + 50):
            manager.challenges[f"c-{index}"] = {
                "user_id": "u",
                "purpose": "login",
                "challenge": b"x",
                "created_at": now + index,
                "expires_at": now + 300,
            }
        manager._cleanup_challenges_unlocked()
        assert len(manager.challenges) <= security_service.MAX_ACTIVE_CHALLENGES
        manager.challenges.clear()


def test_successful_reauth_revokes_previous_server_session(client, monkeypatch):
    old_session_id = authenticate(client)
    monkeypatch.setattr(
        api_auth.security_manager,
        'verify_authentication',
        lambda *args, **kwargs: {'device_id': None, 'device_name': 'Test'},
    )

    resp = client.post(
        '/api/auth/login/verify',
        json={'credential': {}, 'challenge_id': 'c1', 'remember': True},
    )
    assert resp.status_code == 200

    old_record = api_auth.runtime_db.get_security_session(old_session_id)
    assert old_record['revoked_at'] is not None


def test_tunnel_sync_requires_first_local_passkey(client, monkeypatch):
    monkeypatch.setattr(
        api_auth.security_manager,
        'has_credentials',
        lambda _user_id: False,
    )
    resp = client.post(
        '/api/auth/tunnel/sync',
        json={'url': 'https://example.trycloudflare.com'},
        environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
    )
    assert resp.status_code == 409
