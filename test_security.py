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
