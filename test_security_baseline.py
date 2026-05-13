import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

# --- SECURITY REGRESSION TESTS ---

def test_sqli_authentication_bypass_fails(client):
    """Verifies SQLi patch: Payload should not bypass login."""
    response = client.post('/login', data={'username': 'admin', 'password': "' OR '1'='1"}, follow_redirects=True)
    # Check for lowercase 'login' to match your template
    assert b'login' in response.data.lower()

def test_xss_payload_is_escaped(client):
    """Verifies XSS patch: Script tags must be escaped."""
    # Using correct password 'admin'
    client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
    payload = "<script>alert('XSS')</script>"
    client.post('/dashboard', data={'content': payload}, follow_redirects=True)
    response = client.get('/dashboard')
    # Check for escaped characters
    assert b"&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;" in response.data

def test_idor_deletion_fails_unauthenticated(client):
    """Verifies IDOR patch: Unauthenticated users are redirected."""
    response = client.get('/delete/1', follow_redirects=True)
    assert b'login' in response.data.lower()

# --- COVERAGE BOOSTING TESTS ---

def test_signup_functionality(client):
    """Exercises /signup: Should return 200 OK."""
    response = client.get('/signup')
    assert response.status_code == 200

def test_admin_access_denied_for_users(client):
    """Exercises /admin: Should block non-admins with 302 or 403."""
    response = client.get('/admin', follow_redirects=False)
    # Redirect to login or Access Denied are both valid security states
    assert response.status_code in [302, 403]

def test_edit_post_route_access(client):
    """Exercises /edit/<id>: Should redirect if not logged in."""
    response = client.get('/edit/1', follow_redirects=False)
    assert response.status_code == 302

def test_logout_redirects(client):
    """Exercises /logout: Should redirect to login page."""
    response = client.get('/logout', follow_redirects=True)
    assert b'login' in response.data.lower()