import pytest
from app.services.auth_service import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, create_password_reset_token,
    create_email_verification_token,
)


class TestPasswordHashing:
    def test_hash_password_returns_hash(self):
        hashed = hash_password("MySecret123")
        assert hashed != "MySecret123"
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        hashed = hash_password("MySecret123")
        assert verify_password("MySecret123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("MySecret123")
        assert verify_password("WrongPass", hashed) is False

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("Pass1!")
        h2 = hash_password("Pass1!")
        # bcrypt salts ensure different hashes
        assert h1 != h2


class TestJWTTokens:
    def test_create_access_token(self):
        token = create_access_token({"sub": "user-123"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_decode_access_token(self):
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        result = decode_token("totally.invalid.token")
        assert result is None

    def test_password_reset_token(self):
        token = create_password_reset_token("user@example.com")
        payload = decode_token(token)
        assert payload["sub"] == "user@example.com"
        assert payload["type"] == "password_reset"

    def test_email_verification_token(self):
        token = create_email_verification_token("user@example.com")
        payload = decode_token(token)
        assert payload["sub"] == "user@example.com"
        assert payload["type"] == "email_verify"
