"""Optional HTTP Basic gate for the public demo deployment."""

from __future__ import annotations

import base64
import binascii
import os
import secrets
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REALM = "Context Compiler demo"


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Require HTTP Basic credentials when DEMO_AUTH_* are set.

    Leaving either variable unset disables the gate, so local development and
    the test suite are untouched. What it protects is cost, not the host: five
    endpoints spend Anthropic credits on every call and a public URL with no
    gate is an open LLM proxy billed to whoever owns the key.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        user = os.getenv("DEMO_AUTH_USER")
        password = os.getenv("DEMO_AUTH_PASSWORD")
        if not user or not password:
            return await call_next(request)

        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "basic":
            try:
                given = base64.b64decode(token, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                given = ""
            given_user, _, given_password = given.partition(":")
            # Both halves are always compared, so a wrong user costs the same as
            # a wrong password.
            ok_user = secrets.compare_digest(given_user, user)
            ok_password = secrets.compare_digest(given_password, password)
            if ok_user and ok_password:
                return await call_next(request)

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": f'Basic realm="{REALM}", charset="UTF-8"'},
        )
