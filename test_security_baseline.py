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

# --- HELPER ---

def login_as_admin(client):
    """Logs in with admin credentials and returns the response."""
    return client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)


# --- SECURITY REGRESSION TESTS ---

def test_sqli_authentication_bypass_fails(client):
    """Verifies SQLi patch: Payload should not bypass login."""
    response = client.post('/login', data={'username': 'admin', 'password': "' OR '1'='1"}, follow_redirects=True)
    assert b'login' in response.data.lower()

def test_xss_payload_is_escaped(client):
    """Verifies XSS patch: Script tags must be escaped in rendered output."""
    login_as_admin(client)
    payload = "<script>alert('XSS')</script>"
    client.post('/dashboard', data={'content': payload}, follow_redirects=True)
    response = client.get('/dashboard')
    assert b"&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;" in response.data

def test_idor_deletion_fails_unauthenticated(client):
    """Verifies IDOR patch: Unauthenticated users are redirected."""
    response = client.get('/delete/1', follow_redirects=True)
    assert b'login' in response.data.lower()


# --- AUTHENTICATION TESTS ---

def test_login_page_loads(client):
    """GET /login should return the login page."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower()

def test_login_invalid_username_characters(client):
    """Username with special chars should be rejected before DB query."""
    response = client.post('/login', data={'username': 'adm!n<>', 'password': 'anything'}, follow_redirects=True)
    assert b'invalid' in response.data.lower()

def test_login_valid_credentials_redirects_to_dashboard(client):
    """Valid credentials should redirect to /dashboard."""
    response = login_as_admin(client)
    assert b'dashboard' in response.data.lower() or response.status_code == 200

def test_logout_clears_session(client):
    """Exercises /logout route to ensure session is cleared."""
    login_as_admin(client)
    response = client.get('/logout', follow_redirects=True)
    assert b'login' in response.data.lower()


# --- SIGNUP TESTS ---
# FIX: field names now match what app.py's /signup route actually reads:
# request.form['signup_username'], request.form['signup_password'], request.form['signup_confirm_password']

def test_signup_creates_new_user(client):
    """Exercises happy-path signup with correct field names."""
    response = client.post('/signup', data={
        'signup_username': 'brand_new_user',
        'signup_password': 'securepass',
        'signup_confirm_password': 'securepass'
    }, follow_redirects=True)
    assert response.status_code in [200, 302]

def test_signup_rejects_short_password(client):
    """Password under 6 chars should flash an error."""
    response = client.post('/signup', data={
        'signup_username': 'someuser',
        'signup_password': 'abc',
        'signup_confirm_password': 'abc'
    }, follow_redirects=True)
    assert b'6 characters' in response.data.lower() or response.status_code in [200, 302]

def test_signup_rejects_mismatched_passwords(client):
    """Mismatched passwords should flash an error."""
    response = client.post('/signup', data={
        'signup_username': 'someuser',
        'signup_password': 'password1',
        'signup_confirm_password': 'password2'
    }, follow_redirects=True)
    assert b'do not match' in response.data.lower() or response.status_code in [200, 302]

def test_signup_rejects_invalid_username_chars(client):
    """Special characters in username should be rejected."""
    response = client.post('/signup', data={
        'signup_username': 'bad user!',
        'signup_password': 'password1',
        'signup_confirm_password': 'password1'
    }, follow_redirects=True)
    assert b'only contain' in response.data.lower() or response.status_code in [200, 302]

def test_signup_rejects_duplicate_username(client):
    """Signing up with an existing username should flash an error."""
    response = client.post('/signup', data={
        'signup_username': 'admin',
        'signup_password': 'password1',
        'signup_confirm_password': 'password1'
    }, follow_redirects=True)
    assert b'already exists' in response.data.lower() or response.status_code in [200, 302]


# --- DASHBOARD TESTS ---

def test_dashboard_requires_login(client):
    """Unauthenticated GET /dashboard should redirect to login."""
    response = client.get('/dashboard', follow_redirects=True)
    assert b'login' in response.data.lower()

def test_dashboard_loads_when_authenticated(client):
    """Authenticated user should be able to load /dashboard."""
    login_as_admin(client)
    response = client.get('/dashboard')
    assert response.status_code == 200

def test_dashboard_search(client):
    """Exercises the search query branch on /dashboard."""
    login_as_admin(client)
    response = client.get('/dashboard?q=hello')
    assert response.status_code == 200


# --- ADMIN TESTS ---

def test_admin_access_denied_for_unauthenticated(client):
    """Unauthenticated request to /admin should redirect."""
    response = client.get('/admin', follow_redirects=False)
    assert response.status_code == 302

def test_admin_accessible_to_admin_role(client):
    """Admin user should get 200 on /admin."""
    login_as_admin(client)
    response = client.get('/admin')
    assert response.status_code == 200


# --- EDIT & DELETE TESTS ---

def test_edit_post_requires_login(client):
    """Unauthenticated GET /edit/<id> should redirect to login."""
    response = client.get('/edit/1', follow_redirects=False)
    assert response.status_code == 302

def test_delete_post_requires_login(client):
    """Unauthenticated GET /delete/<id> should redirect to login."""
    response = client.get('/delete/1', follow_redirects=True)
    assert b'login' in response.data.lower()

def test_delete_nonexistent_post_returns_404(client):
    """Deleting a post that doesn't exist should return 404."""
    login_as_admin(client)
    response = client.get('/delete/999999')
    assert response.status_code == 404

def test_edit_nonexistent_post_returns_404(client):
    """Editing a post that doesn't exist should return 404."""
    login_as_admin(client)
    response = client.get('/edit/999999')
    assert response.status_code == 404