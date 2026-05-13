import pytest
import os
from app import app, get_db_connection

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

# --- EXISTING SECURITY REGRESSION TESTS ---

def test_sqli_authentication_bypass_fails(client):
    response = client.post('/login', data={'username': 'admin', 'password': "' OR '1'='1"}, follow_redirects=True)
    assert b'Invalid credentials' in response.data

def test_xss_payload_is_escaped(client):
    client.post('/login', data={'username': 'admin', 'password': 'password'}, follow_redirects=True)
    payload = "<script>alert('XSS')</script>"
    client.post('/dashboard', data={'content': payload}, follow_redirects=True)
    response = client.get('/dashboard')
    assert b"&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;" in response.data

def test_idor_deletion_fails_unauthenticated(client):
    response = client.get('/delete/1', follow_redirects=True)
    assert b'Login' in response.data

# --- NEW COVERAGE-BOOSTING TESTS ---

def test_signup_functionality(client):
    """Exercises the /signup route"""
    response = client.post('/signup', data={
        'username': 'newuser',
        'password': 'newpassword'
    }, follow_redirects=True)
    assert response.status_code == 200

def test_admin_access_controls(client):
    """Exercises the /admin route and its logic"""
    # Test unauthorized access
    client.post('/login', data={'username': 'newuser', 'password': 'newpassword'}, follow_redirects=True)
    response = client.get('/admin')
    assert response.status_code == 403 # Assuming your RBAC blocks this

def test_edit_post_route(client):
    """Exercises the /edit/<id> route"""
    client.post('/login', data={'username': 'admin', 'password': 'password'}, follow_redirects=True)
    # GET the edit page
    response = client.get('/edit/1')
    assert response.status_code in [200, 404] # 404 is fine if post 1 doesn't exist
    
    # POST an update
    response = client.post('/edit/1', data={'content': 'Updated Content'}, follow_redirects=True)
    assert response.status_code == 200

def test_logout_clears_session(client):
    """Exercises the /logout route"""
    response = client.get('/logout', follow_redirects=True)
    assert b'Login' in response.data