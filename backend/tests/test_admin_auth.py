import time
import secrets
import hashlib
import hmac
import pytest

from app.services.admin_auth import (
    COOKIE_NAME,
    COOKIE_MAX_AGE_SECONDS,
    _mask_email,
    _session_secret,
    _sign,
    check_login_rate_limit,
    create_admin_session_cookie,
    record_login_attempt,
    verify_admin_password,
    verify_admin_session_cookie,
)


class TestSessionSecret:
    def test_requires_non_empty_secret(self, monkeypatch):
        class FakeSettings:
            admin_session_secret = ""
            supabase_jwt_secret = "should-not-be-used"
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        with pytest.raises(ValueError, match="ADMIN_SESSION_SECRET must be set"):
            _session_secret()

    def test_uses_configured_secret(self, monkeypatch):
        class FakeSettings:
            admin_session_secret = "  test-secret-32-chars-long-enough  "
            supabase_jwt_secret = "should-not-be-used"
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        assert _session_secret() == "test-secret-32-chars-long-enough"

    def test_no_jwt_secret_fallback(self, monkeypatch):
        class FakeSettings:
            admin_session_secret = "  actual-secret-32-chars-long-enough  "
            supabase_jwt_secret = "jwt-secret-should-not-be-fallback"
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        result = _session_secret()
        assert result == "actual-secret-32-chars-long-enough"
        assert "jwt" not in result


class TestCookieSession:
    def test_create_and_verify_round_trip(self, monkeypatch):
        class FakeSettings:
            admin_session_secret = "a" * 64
            supabase_jwt_secret = "unused"
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        cookie = create_admin_session_cookie()
        assert verify_admin_session_cookie(cookie) is True

    def test_verify_rejects_empty(self, monkeypatch):
        class FakeSettings:
            admin_session_secret = "a" * 64
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        assert verify_admin_session_cookie(None) is False
        assert verify_admin_session_cookie("") is False

    def test_verify_rejects_tampered(self, monkeypatch):
        class FakeSettings:
            admin_session_secret = "a" * 64
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        cookie = create_admin_session_cookie()
        tampered = cookie[:-5] + "xxxxx"
        assert verify_admin_session_cookie(tampered) is False

    def test_verify_rejects_expired(self, monkeypatch):
        class FakeSettings:
            admin_session_secret = "a" * 64
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        issued_at = str(int(time.time()) - COOKIE_MAX_AGE_SECONDS - 100)
        nonce = secrets.token_hex(8)
        payload = f"{issued_at}:{nonce}"
        sig = hmac.new(
            "a" * 64, payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        expired_cookie = f"{payload}.{sig}"
        assert verify_admin_session_cookie(expired_cookie) is False


class TestPasswordVerification:
    def test_correct_password(self, monkeypatch):
        class FakeSettings:
            admin_password = "correct-password"
            admin_session_secret = "a" * 64
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        assert verify_admin_password("correct-password") is True

    def test_wrong_password(self, monkeypatch):
        class FakeSettings:
            admin_password = "correct-password"
            admin_session_secret = "a" * 64
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        assert verify_admin_password("wrong-password") is False

    def test_empty_password_returns_503(self, monkeypatch):
        from fastapi import HTTPException
        class FakeSettings:
            admin_password = ""
            admin_session_secret = "a" * 64
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        with pytest.raises(HTTPException) as exc:
            verify_admin_password("anything")
        assert exc.value.status_code == 503

    def test_timing_safe_comparison(self, monkeypatch):
        class FakeSettings:
            admin_password = "a" * 64
            admin_session_secret = "b" * 64
        monkeypatch.setattr("app.services.admin_auth.get_settings", lambda: FakeSettings())
        assert verify_admin_password("a" * 64) is True
        assert verify_admin_password("a" * 63 + "b") is False


class TestRateLimiting:
    def test_allows_under_limit(self, monkeypatch):
        ip = "1.2.3.4"
        for _ in range(4):
            record_login_attempt(ip)
        check_login_rate_limit(ip)

    def test_blocks_over_limit(self, monkeypatch):
        from fastapi import HTTPException
        ip = "5.6.7.8"
        for _ in range(5):
            record_login_attempt(ip)
        with pytest.raises(HTTPException) as exc:
            check_login_rate_limit(ip)
        assert exc.value.status_code == 429

    def test_separate_ips_independent(self):
        from fastapi import HTTPException
        ip_a = "10.0.0.1"
        ip_b = "10.0.0.2"
        for _ in range(5):
            record_login_attempt(ip_a)
        with pytest.raises(HTTPException):
            check_login_rate_limit(ip_a)
        check_login_rate_limit(ip_b)


class TestEmailMasking:
    def test_normal_email(self):
        assert _mask_email("john.doe@gmail.com") == "j***e@gmail.com"

    def test_short_email(self):
        assert _mask_email("ab@gmail.com") == "**@gmail.com"

    def test_two_char_local(self):
        assert _mask_email("jo@gmail.com") == "**@gmail.com"

    def test_none(self):
        assert _mask_email(None) is None

    def test_no_at_sign(self):
        assert _mask_email("notanemail") == "notanemail"