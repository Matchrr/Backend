import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import xano_auth
from app.services.xano_auth import XanoAuthError, XanoUser


def test_request_password_reset_hides_unknown_email(monkeypatch):
    def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/reset/request-reset-link"
        assert kwargs["params"]["email"] == "nobody@example.com"
        assert kwargs["params"]["origin"] == "http://localhost:3000"
        raise XanoAuthError("No user found for that email.", status_code=404)

    monkeypatch.setattr(xano_auth, "_request", fake_request)
    xano_auth.request_password_reset("nobody@example.com", origin="http://localhost:3000/")


def test_request_password_reset_surfaces_missing_endpoints(monkeypatch):
    def fake_request(method, path, **kwargs):
        raise XanoAuthError("missing", status_code=503, code="auth_endpoints_missing")

    monkeypatch.setattr(xano_auth, "_request", fake_request)
    with pytest.raises(XanoAuthError) as caught:
        xano_auth.request_password_reset("ada@example.com")
    assert caught.value.status_code == 503


def test_reset_password_exchanges_magic_token_then_updates(monkeypatch):
    calls: list[tuple[str, str]] = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path))
        if path == "/reset/magic-link-login":
            assert kwargs["json"] == {
                "email": "ada@example.com",
                "magic_token": "magic-uuid-token-value",
            }
            return {"authToken": "header.payload.sig", "user_id": 9}
        if path == "/reset/update_password":
            assert kwargs["token"] == "header.payload.sig"
            assert kwargs["json"]["password"] == "Secret123"
            assert kwargs["json"]["confirm_password"] == "Secret123"
            return {"message": {"success": "true"}}
        if path == "/auth/me":
            return {"id": 9, "email": "ada@example.com", "name": "Ada"}
        raise AssertionError(path)

    monkeypatch.setattr(xano_auth, "_request", fake_request)
    token, user = xano_auth.reset_password("ada@example.com", "magic-uuid-token-value", "Secret123")
    assert token == "header.payload.sig"
    assert user.email == "ada@example.com"
    assert calls == [
        ("POST", "/reset/magic-link-login"),
        ("POST", "/reset/update_password"),
        ("GET", "/auth/me"),
    ]


def test_reset_password_rejects_password_without_a_digit():
    with pytest.raises(XanoAuthError) as caught:
        xano_auth.reset_password("ada@example.com", "magic-uuid-token-value", "password")
    assert caught.value.status_code == 400
    assert "number" in str(caught.value).lower()


def test_reset_password_rewrites_broken_magic_token_errors(monkeypatch):
    def fake_request(method, path, **kwargs):
        raise XanoAuthError("Unable to locate var: user.password_reset.token", status_code=400)

    monkeypatch.setattr(xano_auth, "_request", fake_request)
    with pytest.raises(XanoAuthError) as caught:
        xano_auth.reset_password("ada@example.com", "magic-uuid-token-value", "Secret123")
    assert caught.value.status_code == 400
    assert "invalid or has expired" in str(caught.value).lower()


def test_forgot_password_route_is_public(monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.request_password_reset", lambda email, origin=None: None)
    monkeypatch.setattr("app.core.auth.auth_is_required", lambda: True)
    client = TestClient(app)
    response = client.post("/api/auth/forgot-password", json={"email": "ada@example.com"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reset_password_route_returns_session(monkeypatch):
    user = XanoUser(id="9", email="ada@example.com", name="Ada", raw={"id": 9})

    def fake_reset(email, token, password):
        assert email == "ada@example.com"
        assert token == "magic-uuid-token-value"
        assert password == "Secret123"
        return "header.payload.sig", user

    monkeypatch.setattr("app.api.routes.auth.reset_password", fake_reset)
    monkeypatch.setattr("app.core.auth.auth_is_required", lambda: True)
    monkeypatch.setattr("app.services.store.store.bind_identity", lambda *args, **kwargs: None)
    client = TestClient(app)
    response = client.post(
        "/api/auth/reset-password",
        json={
            "email": "ada@example.com",
            "token": "magic-uuid-token-value",
            "password": "Secret123",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "header.payload.sig"
    assert body["user"]["email"] == "ada@example.com"
