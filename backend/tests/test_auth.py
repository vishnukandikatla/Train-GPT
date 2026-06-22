import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    # Helper to clean up test users from the database before/after tests
    from backend.database.mongodb import get_db
    db = get_db()
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def delete_users():
        # Find all users and filter by prefix in python to be DB-agnostic
        cursor = db.users.find({})
        users = await cursor.to_list()
        for u in users:
            email = u.get("email", "")
            if email.startswith("test_") or email.startswith("google_") or email.startswith("github_") or email.startswith("guest_"):
                await db.users.delete_one({"_id": u["_id"]})
        
        # Delete exact email test tokens
        await db.reset_tokens.delete_one({"email": "test_reset@example.com"})

    loop.run_until_complete(delete_users())
    yield
    loop.run_until_complete(delete_users())


def test_register_success():
    payload = {
        "name": "Test User",
        "email": "test_register@example.com",
        "password": "testpassword123",
        "confirmPassword": "testpassword123"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["name"] == "Test User"
    assert data["user"]["email"] == "test_register@example.com"
    assert data["user"]["role"] == "user"
    assert data["user"]["provider"] == "local"


def test_register_duplicate_email():
    payload = {
        "name": "Test User 1",
        "email": "test_duplicate@example.com",
        "password": "testpassword123",
        "confirmPassword": "testpassword123"
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 200

    # Register again with same email
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"]


def test_register_validation_errors():
    # Mismatched password
    res_mismatch = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test_mismatch@example.com",
        "password": "password123",
        "confirmPassword": "password_different"
    })
    assert res_mismatch.status_code == 422

    # Invalid email format
    res_invalid_email = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "invalid_email_format",
        "password": "password123",
        "confirmPassword": "password123"
    })
    assert res_invalid_email.status_code == 422

    # Password too short
    res_short = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test_short@example.com",
        "password": "123",
        "confirmPassword": "123"
    })
    assert res_short.status_code == 422


def test_login_success():
    # First register the user
    payload = {
        "name": "Test User",
        "email": "test_login@example.com",
        "password": "testpassword123",
        "confirmPassword": "testpassword123"
    }
    client.post("/api/auth/register", json=payload)

    # Try login
    res = client.post("/api/auth/login", json={
        "email": "test_login@example.com",
        "password": "testpassword123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_login@example.com"
    assert data["user"]["lastLogin"] is not None


def test_login_wrong_password_and_missing_user():
    # First register user
    payload = {
        "name": "Test User",
        "email": "test_wrong_pwd@example.com",
        "password": "testpassword123",
        "confirmPassword": "testpassword123"
    }
    client.post("/api/auth/register", json=payload)

    # Wrong password login
    res_wrong = client.post("/api/auth/login", json={
        "email": "test_wrong_pwd@example.com",
        "password": "wrongpassword"
    })
    assert res_wrong.status_code == 400
    assert "Incorrect email or password" in res_wrong.json()["detail"]

    # Non-existent user login
    res_missing = client.post("/api/auth/login", json={
        "email": "test_not_exists@example.com",
        "password": "password123"
    })
    assert res_missing.status_code == 400
    assert "Incorrect email or password" in res_missing.json()["detail"]


def test_google_login():
    payload = {
        "token": "mock_google_token_test_google@example.com",
        "email": "test_google@example.com",
        "name": "Google Tester"
    }
    res = client.post("/api/auth/google", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_google@example.com"
    assert data["user"]["provider"] == "google"
    assert data["user"]["role"] == "user"


def test_github_login():
    payload = {
        "token": "mock_github_token_test_github@example.com",
        "email": "test_github@example.com",
        "name": "GitHub Tester"
    }
    res = client.post("/api/auth/github", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_github@example.com"
    assert data["user"]["provider"] == "github"
    assert data["user"]["role"] == "user"


def test_guest_login():
    res = client.post("/api/auth/guest")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["provider"] == "guest"
    assert data["user"]["role"] == "guest"
    assert "guest_" in data["user"]["email"]


def test_profile_and_logout_endpoints():
    # Register user
    payload = {
        "name": "Test User",
        "email": "test_profile@example.com",
        "password": "testpassword123",
        "confirmPassword": "testpassword123"
    }
    reg_res = client.post("/api/auth/register", json=payload)
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch profile (Standard Auth Route)
    res_profile = client.get("/api/auth/profile", headers=headers)
    assert res_profile.status_code == 200
    assert res_profile.json()["email"] == "test_profile@example.com"

    # Fetch profile (Legacy Fallback Route)
    res_legacy_profile = client.get("/api/profile", headers=headers)
    assert res_legacy_profile.status_code == 200
    assert res_legacy_profile.json()["email"] == "test_profile@example.com"

    # Try profile without headers
    res_unauth = client.get("/api/auth/profile")
    assert res_unauth.status_code in [401, 403] # Missing Bearer token

    # Logout (Standard Auth Route)
    res_logout = client.post("/api/auth/logout", headers=headers)
    assert res_logout.status_code == 200
    assert res_logout.json()["status"] == "success"

    # Logout (Legacy Fallback Route)
    res_legacy_logout = client.post("/api/logout", headers=headers)
    assert res_legacy_logout.status_code == 200
    assert res_legacy_logout.json()["status"] == "success"


def test_forgot_and_reset_password_flow():
    # Register user
    payload = {
        "name": "Reset Tester",
        "email": "test_reset@example.com",
        "password": "originalpassword",
        "confirmPassword": "originalpassword"
    }
    client.post("/api/auth/register", json=payload)

    # Request password reset token
    res_forgot = client.post("/api/auth/forgot-password", json={"email": "test_reset@example.com"})
    assert res_forgot.status_code == 200
    
    # Retrieve the token from mock database directly (to simulate email retrieval)
    from backend.database.mongodb import get_db
    import asyncio
    db = get_db()
    token_doc = asyncio.run(db.reset_tokens.find_one({"email": "test_reset@example.com"}))
    assert token_doc is not None
    token = token_doc["token"]

    # Reset password with token
    res_reset = client.post("/api/auth/reset-password", json={
        "token": token,
        "newPassword": "newpassword123",
        "confirmPassword": "newpassword123"
    })
    assert res_reset.status_code == 200

    # Try login with new password
    res_login = client.post("/api/auth/login", json={
        "email": "test_reset@example.com",
        "password": "newpassword123"
    })
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()
