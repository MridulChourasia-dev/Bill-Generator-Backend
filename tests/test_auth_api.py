import pytest


class TestUserRegistration:
    def test_register_success(self, client, test_user_data):
        response = client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, test_user_data, registered_user):
        response = client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_register_weak_password(self, client):
        data = {
            "email": "new@example.com",
            "username": "newuser",
            "password": "weak",
            "full_name": "New User",
        }
        response = client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        data = {
            "email": "not-an-email",
            "username": "user2",
            "password": "StrongPass123",
        }
        response = client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422


class TestUserLogin:
    def test_login_success(self, client, test_user_data, registered_user):
        response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user_data, registered_user):
        response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": "WrongPassword123",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "AnyPass123",
        })
        assert response.status_code == 401


class TestGetCurrentUser:
    def test_get_me_authenticated(self, client, registered_user, auth_headers):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["email"]

    def test_get_me_unauthenticated(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestRefreshToken:
    def test_refresh_token(self, client, test_user_data, registered_user):
        login_resp = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        refresh_token = login_resp.json()["refresh_token"]
        response = client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_with_invalid_token(self, client):
        response = client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401
