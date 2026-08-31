from urllib.parse import urlparse

import pytest

from app.services import google_auth, xano_auth
from app.services.xano_auth import XanoAuthError


def test_login_with_google_calls_xano_find_or_create(monkeypatch):
    captured: dict = {}

    def fake_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs["json"]
        return {"authToken": "header.payload.sig", "user_id": 11}

    monkeypatch.setattr(xano_auth, "_request", fake_request)
    monkeypatch.setattr(
        xano_auth,
        "fetch_me",
        lambda token: xano_auth.XanoUser(
            id="11",
            email="ada@gmail.com",
            name="Ada",
            raw={"id": 11, "email": "ada@gmail.com"},
        ),
    )

    token, user = xano_auth.login_with_google("Ada@Gmail.com", "Ada", "google-sub-1", "Secret123Aa")
    assert token == "header.payload.sig"
    assert user.email == "ada@gmail.com"
    assert captured["path"] == "/auth/google"
    assert captured["json"]["google_id"] == "google-sub-1"
    assert captured["json"]["email"] == "ada@gmail.com"


def test_login_with_google_surfaces_missing_endpoint(monkeypatch):
    def fake_request(method, path, **kwargs):
        raise XanoAuthError("missing", status_code=503, code="auth_endpoints_missing")

    monkeypatch.setattr(xano_auth, "_request", fake_request)
    with pytest.raises(XanoAuthError) as caught:
        xano_auth.login_with_google("ada@gmail.com", "Ada", "sub", "Secret123Aa")
    assert caught.value.status_code == 503


def test_google_authorize_url_includes_openid_scopes(monkeypatch):
    monkeypatch.setattr(google_auth.settings, "google_client_id", "client.apps.googleusercontent.com")
    monkeypatch.setattr(google_auth.settings, "google_client_secret", "secret")
    monkeypatch.setattr(
        google_auth.settings,
        "google_redirect_uri",
        "http://localhost:4000/api/auth/google/callback",
    )
    url = google_auth.build_authorization_url()
    parsed = urlparse(url)
    assert parsed.netloc == "accounts.google.com"
    assert "openid" in parsed.query
    assert "email" in parsed.query
    assert "state=" in parsed.query


def test_google_complete_login_rejects_bad_state(monkeypatch):
    monkeypatch.setattr(google_auth.settings, "google_client_id", "client")
    monkeypatch.setattr(google_auth.settings, "google_client_secret", "secret")
    with pytest.raises(google_auth.GoogleAuthError):
        google_auth.complete_login("code", "unknown-state")
