import pytest
import os
import json
from unittest.mock import patch, MagicMock
from webfilm import app
from test_helpers import authenticate_client

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Configure a mock secret key or sessions if needed
    with app.test_client() as client:
        yield client

def test_media_endpoints_unauthorized(client):
    # Streaming endpoint without authentication should yield 401
    resp = client.get('/api/stream?path=D:/CinemaProject/webfilm.py')
    assert resp.status_code == 401
    
    # Thumbnail endpoint without authentication should yield 401
    resp = client.get('/api/thumbnail?path=D:/CinemaProject/webfilm.py')
    assert resp.status_code == 401

    # Preview endpoint without authentication should yield 401
    resp = client.get('/api/preview?path=D:/CinemaProject/webfilm.py')
    assert resp.status_code == 401

def test_tunnel_sync_remote_blocked(client):
    # Remote sync from non-localhost should return 403
    resp = client.post('/api/auth/tunnel/sync', 
                       json={"url": "https://attacker.trycloudflare.com", "token": "evil-token"},
                       environ_overrides={'REMOTE_ADDR': '192.168.1.100'})
    assert resp.status_code == 403

def test_path_traversal_access_denied(client):
    authenticate_client(client)
        
    # Attempting to read outside video_dirs (even with authenticated session) should return 403
    resp = client.get('/api/stream?path=C:/Windows/win.ini')
    assert resp.status_code == 403
    
    # Check delete file traversal
    resp = client.post('/api/delete_file', json={"path": "C:/Windows/win.ini"})
    assert resp.status_code == 403

def test_upload_actor_image_traversal_protection(client):
    authenticate_client(client)

    # Attempting traversal in the name parameter
    from io import BytesIO
    data = {
        'name': '../../api_ai',
        'image': (BytesIO(b"dummy image data"), 'test.jpg')
    }
    resp = client.post('/api/admin/upload_actor_image', data=data, content_type='multipart/form-data')
    # secure_filename converts "../../api_ai" to "api_ai" which resolves to a safe path.
    # If the resolving safe path fails check_path_safe, it might return 403, or 200 if successful in saving to static/img/actors.
    # In any case, it should NOT write to the root project folder (../../api_ai.jpg).
    assert resp.status_code in [403, 415]
    assert not os.path.exists("api_ai.jpg")

def test_actor_image_case_insensitive_auth(client):
    # Unauthenticated access to actor images must be denied regardless of URL case
    resp1 = client.get('/static/img/actors/api_ai.jpg')
    assert resp1.status_code == 401

    resp2 = client.get('/static/IMG/actors/api_ai.jpg')
    assert resp2.status_code == 401

    resp3 = client.get('/static/Img/actors/api_ai.jpg')
    assert resp3.status_code == 401

def test_safe_next_path_and_backslash(client):
    from web_security import _safe_next_path
    with app.test_request_context('/\\evil.com'):
        assert _safe_next_path() == '/'

def test_get_origin_rejects_unallowed_forwarded_host(client):
    from routes.api_auth import get_origin
    with patch.dict(os.environ, {'CINEMA_ALLOWED_HOSTS': 'jp.vivutrade.io.vn', 'CINEMA_PUBLIC_URL': 'https://jp.vivutrade.io.vn'}):
        with app.test_request_context(
            '/api/auth/logout',
            method='POST',
            headers={'Host': 'jp.vivutrade.io.vn', 'X-Forwarded-Host': 'evil.com', 'CF-Connecting-IP': '1.2.3.4'},
            environ_base={'REMOTE_ADDR': '127.0.0.1'}
        ):
            origin = get_origin()
            assert 'evil.com' not in origin
            assert origin == 'https://jp.vivutrade.io.vn'


def test_actor_image_windows_trailing_dot_auth(client):
    # Trailing dot and space bypass variants must be denied without auth
    resp1 = client.get('/static/img/actors./api_ai.jpg')
    assert resp1.status_code == 401

    resp2 = client.get('/static/img/actors%20/api_ai.jpg')
    assert resp2.status_code == 401

    resp3 = client.get('/static/img/actors.../api_ai.jpg')
    assert resp3.status_code == 401


def test_actor_image_api_endpoint(client):
    # Unauthenticated access to /api/actor_image/<filename> must return 401
    resp = client.get('/api/actor_image/api_ai.jpg')
    assert resp.status_code == 401

    # Authenticated access
    authenticate_client(client)
    resp_auth = client.get('/api/actor_image/api_ai.jpg')
    if os.path.exists('data/actors/api_ai.jpg'):
        assert resp_auth.status_code == 200
        assert 'no-store' in resp_auth.headers.get('Cache-Control', '')

    # Missing file returns 404
    resp_missing = client.get('/api/actor_image/nonexistent_idol_xyz.jpg')
    assert resp_missing.status_code == 404

    # Traversal attempt returns 403 or 404
    resp_traversal = client.get('/api/actor_image/../../webfilm.py')
    assert resp_traversal.status_code in [403, 404]


def test_safe_next_path_normalization(client):
    from web_security import _safe_next_path

    # Protocol-relative and path normalization bypass attempts
    for evil in [
        '/.//evil.com',
        '/%2e//evil.com',
        '/..//evil.com',
        '//evil.com',
        r'/\\evil.com',
        r'/\\\\evil.com',
        '//attacker.com/test',
        '///attacker.com',
    ]:
        assert _safe_next_path(evil) == '/', f'Failed direct sanitize evil path: {evil}'

    # In request context
    for evil in [
        '/.//evil.com',
        '/%2e//evil.com',
        '/..//evil.com',
        '//evil.com',
        r'/\\evil.com',
        r'/\\\\evil.com',
        '//attacker.com/test',
    ]:
        with app.test_request_context(evil):
            assert _safe_next_path() == '/', f'Failed context sanitize evil path: {evil}'

    # Legitimate paths should be preserved
    with app.test_request_context('/catalog/film-1'):
        assert _safe_next_path() == '/catalog/film-1'
    assert _safe_next_path('/catalog/film-1') == '/catalog/film-1'

    with app.test_request_context('/'):
        assert _safe_next_path() == '/'
    assert _safe_next_path('/') == '/'


def test_unconfigured_tunnel_forwarded_host_rejected(client):
    from routes.api_auth import get_origin
    from web_security import _allowed_host

    with patch.dict(os.environ, {
        'CINEMA_ALLOWED_HOSTS': 'jp.vivutrade.io.vn',
        'CINEMA_PUBLIC_URL': 'https://jp.vivutrade.io.vn',
        'TUNNEL_URL': 'https://my-legit.trycloudflare.com',
    }):
        # Legitimate configured tunnel is accepted
        with app.test_request_context(
            '/',
            headers={'Host': 'jp.vivutrade.io.vn', 'X-Forwarded-Host': 'my-legit.trycloudflare.com'},
            environ_base={'REMOTE_ADDR': '127.0.0.1'},
        ):
            assert _allowed_host() is True
            assert get_origin() == 'https://my-legit.trycloudflare.com'

        # Unconfigured attacker tunnel is rejected
        with app.test_request_context(
            '/',
            headers={'Host': 'jp.vivutrade.io.vn', 'X-Forwarded-Host': 'attacker.trycloudflare.com'},
            environ_base={'REMOTE_ADDR': '127.0.0.1'},
        ):
            origin = get_origin()
            assert 'attacker.trycloudflare.com' not in origin
