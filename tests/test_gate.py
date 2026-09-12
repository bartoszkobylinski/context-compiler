"""Regression cover for the HTTP Basic gate.

Narrow on purpose: Codex's broader suite (tests/test_serve_frontend.py) never
landed in the repo, so this file guards only the bug it reported plus enough of
the gate's contract that a silent regression cannot disable it.
"""

from __future__ import annotations

import base64

import pytest
from starlette.testclient import TestClient

from backend.main import app


def _auth(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def gated(monkeypatch) -> TestClient:
    monkeypatch.setenv("DEMO_AUTH_USER", "jury")
    monkeypatch.setenv("DEMO_AUTH_PASSWORD", "testpass")
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def ungated(monkeypatch) -> TestClient:
    monkeypatch.delenv("DEMO_AUTH_USER", raising=False)
    monkeypatch.delenv("DEMO_AUTH_PASSWORD", raising=False)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "user,password",
    [
        ("üser", "testpass"),
        ("jury", "hasloł"),
        ("üß☃", "üß☃"),
    ],
)
def test_non_ascii_credentials_are_rejected_not_crashed(gated, user, password):
    """Non-ASCII credentials must answer 401.

    secrets.compare_digest raises TypeError on str with non-ASCII characters,
    which surfaced as 500. The challenge advertises charset="UTF-8", so these
    requests are invited and must be answered, not crashed on.
    """
    response = gated.get("/health", headers=_auth(user, password))
    assert response.status_code == 401


def test_correct_credentials_pass(gated):
    assert gated.get("/health", headers=_auth("jury", "testpass")).status_code == 200


@pytest.mark.parametrize("user,password", [("nope", "testpass"), ("jury", "nope")])
def test_wrong_half_is_rejected(gated, user, password):
    assert gated.get("/health", headers=_auth(user, password)).status_code == 401


@pytest.mark.parametrize("path", ["/", "/health", "/app.js", "/demo-cases"])
def test_gate_covers_api_and_static_mount(gated, path):
    response = gated.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic ")


@pytest.mark.parametrize("header", ["Basic !!!notbase64", "Basic ", "Bearer abc", "garbage"])
def test_malformed_authorization_is_rejected_not_crashed(gated, header):
    response = gated.get("/health", headers={"Authorization": header})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"DEMO_AUTH_USER": "jury"},
        {"DEMO_AUTH_PASSWORD": "testpass"},
        {"DEMO_AUTH_USER": "", "DEMO_AUTH_PASSWORD": "testpass"},
        {"DEMO_AUTH_USER": "jury", "DEMO_AUTH_PASSWORD": ""},
    ],
)
def test_gate_is_a_noop_unless_both_halves_are_set(ungated, monkeypatch, env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert ungated.get("/health").status_code == 200
