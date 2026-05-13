import pytest
import os
from app import app, get_db_connection

@pytest.fixture
def client():
    # Configure the app for testing
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Create a test client
    with app.test_client() as client:
        with app.app_context():
            # You could initialize a test DB here if needed
            pass
        yield client

def test_sqli_authentication_bypass_fails(client):
    """
    REGRESSION TEST: Ensures the SQL Injection patch is active.
    Attempts to log in with the classic ' OR '1'='1 payload.
    Should fail to redirect to dashboard.
    """
    response = client.post('/login', data={
        'username': 'admin',
        'password': "' OR '1'='1"
    }, follow_redirects=True)
    
    # The login should fail and keep us on the login page with an error
    assert b'Invalid credentials' in response.data or b'Invalid characters' in response.data

def test_xss_payload_is_escaped(client):
    """
    REGRESSION TEST: Ensures the Stored XSS patch (Jinja autoescape) is active.
    Posts a script tag and verifies it is rendered harmlessly as text.
    """
    # 1. Log in as a valid user (assuming 'admin'/'admin' exists in your DB for this test)
    client.post('/login', data={'username': 'admin', 'password': 'password'})
    
    # 2. Submit the XSS payload
    payload = "<script>alert('XSS')</script>"
    client.post('/dashboard', data={'content': payload})
    
    # 3. Fetch the dashboard and check if it was escaped
    response = client.get('/dashboard')
    
    # The raw script tag should NOT be in the HTML, it should be encoded
    assert b"<script>alert('XSS')</script>" not in response.data
    assert b"&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;" in response.data

def test_idor_deletion_fails(client):
    """
    REGRESSION TEST: Ensures the IDOR/RBAC patch is active on the delete route.
    """
    # Assuming post ID 9 is the admin post we tried to delete earlier
    response = client.get('/delete/9', follow_redirects=False)
    
    # Because we are not logged in, it should redirect to login (302) 
    # OR if logged in as wrong user, return Access Denied (403)
    assert response.status_code in [302, 403]