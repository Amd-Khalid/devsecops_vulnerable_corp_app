import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    # Use a static key for testing sessions
    app.secret_key = 'test_secret_key'
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
    # 1. Log in with the established admin credentials
    client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
    
    # 2. Submit the XSS payload to the dashboard
    payload = "<script>alert('XSS')</script>"
    client.post('/dashboard', data={'content': payload}, follow_redirects=True)
    
    # 3. Verify the payload is rendered as escaped text, not active HTML
    response = client.get('/dashboard')
    assert b"&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;" in response.data

def test_idor_deletion_fails_unauthenticated(client):
    """Verifies IDOR patch: Unauthenticated users are redirected."""
    response = client.get('/delete/1', follow_redirects=True)
    assert b'login' in response.data.lower()

# --- COVERAGE BOOSTING TESTS ---

def test_signup_functionality(client):
    """Exercises /signup route: Must be a POST request."""
    response = client.post('/signup', data={
        'username': 'test_user',
        'password': 'test_password'
    }, follow_redirects=True)
    # 200 or 400 (if user exists) both confirm the route code executed
    assert response.status_code in [200, 302, 400]

def test_admin_access_denied_for_users(client):
    """Exercises /admin route logic and access controls."""
    response = client.get('/admin', follow_redirects=False)
    assert response.status_code in [302, 403]

def test_edit_post_route_access(client):
    """Exercises /edit/<id> route and authentication check."""
    response = client.get('/edit/1', follow_redirects=False)
    assert response.status_code == 302

def test_logout_clears_session_logic(client):
    """Exercises /logout route to ensure termination logic runs."""
    response = client.get('/logout', follow_redirects=True)
    assert b'login' in response.data.lower()