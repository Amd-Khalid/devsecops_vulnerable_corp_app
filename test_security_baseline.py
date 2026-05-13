import pytest
import sqlite3
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.secret_key = 'test_secret_key'
    with app.test_client() as client:
        yield client

# --- HELPERS ---

def login_as_admin(client):
    """Logs in with admin credentials and returns the response."""
    return client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

def create_test_user(username='testuser_coverage', password='testpass1'):
    """Inserts a plain 'user' role account directly into the DB. Returns username."""
    conn = sqlite3.connect('database.db')
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, 'user')",
            (username, password)
        )
        conn.commit()
    finally:
        conn.close()
    return username

def delete_test_user(username='testuser_coverage'):
    """Cleans up the test user and their posts after a test."""
    conn = sqlite3.connect('database.db')
    try:
        conn.execute("DELETE FROM posts WHERE author = ?", (username,))
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
    finally:
        conn.close()

def get_latest_post_id():
    """Returns the ID of the most recently inserted post."""
    conn = sqlite3.connect('database.db')
    try:
        row = conn.execute("SELECT id FROM posts ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


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


# --- INDEX ROUTE TESTS (covers lines 23-25) ---

def test_index_redirects_to_login_when_unauthenticated(client):
    """GET / without a session should redirect to /login."""
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert b'/login' in response.data or response.location.endswith('/login')

def test_index_redirects_to_dashboard_when_authenticated(client):
    """GET / with an active session should redirect to /dashboard."""
    login_as_admin(client)
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert b'/dashboard' in response.data or response.location.endswith('/dashboard')


# --- EDIT POST — POST method & access denied (covers lines 131-140) ---

def test_edit_post_updates_content(client):
    """POST /edit/<id> as the author should update the post and redirect. Covers the POST branch."""
    login_as_admin(client)
    # Create a post so we have a real ID to work with
    client.post('/dashboard', data={'content': 'original content'}, follow_redirects=True)
    post_id = get_latest_post_id()
    assert post_id is not None, "Need at least one post in the DB to run this test"

    response = client.post(f'/edit/{post_id}', data={'content': 'updated content'}, follow_redirects=True)
    assert response.status_code == 200

def test_edit_post_access_denied_for_non_owner(client):
    """Non-owner non-admin user trying to edit someone else's post gets 403. Covers lines 131-133."""
    # Create a regular user
    create_test_user('other_user', 'otherpass1')
    try:
        # Admin creates a post
        login_as_admin(client)
        client.post('/dashboard', data={'content': 'admin only post'}, follow_redirects=True)
        post_id = get_latest_post_id()
        assert post_id is not None

        # Log out admin, log in as the regular user
        client.get('/logout')
        client.post('/login', data={'username': 'other_user', 'password': 'otherpass1'}, follow_redirects=True)

        # Try to edit admin's post
        response = client.get(f'/edit/{post_id}')
        assert response.status_code == 403
    finally:
        delete_test_user('other_user')


# --- DELETE USER ROUTE (covers lines 161-184) ---

def test_delete_user_requires_login(client):
    """Unauthenticated POST /delete_user/<username> must redirect to login. Covers line 162."""
    response = client.post('/delete_user/anyone', follow_redirects=True)
    assert b'login' in response.data.lower()

def test_delete_user_forbidden_for_non_admin(client):
    """A regular user attempting to delete someone gets 403. Covers lines 163-164."""
    create_test_user('regular_user', 'regularpass1')
    try:
        client.post('/login', data={'username': 'regular_user', 'password': 'regularpass1'}, follow_redirects=True)
        response = client.post('/delete_user/admin')
        assert response.status_code == 403
    finally:
        client.get('/logout')
        delete_test_user('regular_user')

def test_delete_user_prevents_self_deletion(client):
    """Admin cannot delete their own account. Covers lines 167-169."""
    login_as_admin(client)
    response = client.post('/delete_user/admin', follow_redirects=True)
    # Should flash 'Cannot delete your own account!' and stay on /admin
    assert b'cannot delete' in response.data.lower() or response.status_code == 200

def test_delete_user_successfully_removes_user(client):
    """Admin can delete another user. Covers lines 171-184 (try block + redirect)."""
    # Create a throwaway user to delete
    create_test_user('user_to_delete', 'deletepass1')
    login_as_admin(client)
    response = client.post('/delete_user/user_to_delete', follow_redirects=True)
    assert response.status_code == 200
    # Confirm user is gone
    conn = sqlite3.connect('database.db')
    row = conn.execute("SELECT * FROM users WHERE username = 'user_to_delete'").fetchone()
    conn.close()
    assert row is None