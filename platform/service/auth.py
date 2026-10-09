"""Entra ID bearer-token validation for the platform's HTTP APIs (fail closed)."""

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class AuthError(Exception):
    pass


class EntraTokenValidator:
    """Validates signature, issuer, audience and expiry of an Entra-issued access token.

    ``key_resolver`` maps a token to its signing key; it defaults to the tenant's JWKS endpoint
    and can be replaced in tests.
    """

    def __init__(self, tenant_id: str, audience: str | list[str], *, key_resolver: Callable | None = None):
        if not tenant_id or not audience:
            raise ValueError("tenant_id and audience are required")
        self._audience = audience
        self._issuers = [
            f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            f"https://sts.windows.net/{tenant_id}/",
        ]
        if key_resolver is None:
            jwks = jwt.PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys")
            key_resolver = lambda token: jwks.get_signing_key_from_jwt(token).key  # noqa: E731
        self._key_resolver = key_resolver

    def validate(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self._key_resolver(token),
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuers,
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.PyJWTError as e:
            raise AuthError(str(e)) from e


def _granted(claims: dict) -> set[str]:
    return set(claims.get("roles", [])) | set(str(claims.get("scp", "")).split())


def require_roles(validator: EntraTokenValidator, *needed: str):
    """FastAPI dependency: valid token carrying at least one of ``needed`` (app role or delegated scope)."""
    bearer = HTTPBearer(auto_error=False)

    def dependency(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
        if creds is None:
            raise HTTPException(401, "missing bearer token", headers={"WWW-Authenticate": "Bearer"})
        try:
            claims = validator.validate(creds.credentials)
        except AuthError as e:
            raise HTTPException(401, f"invalid token: {e}", headers={"WWW-Authenticate": "Bearer"}) from e
        if needed and not (_granted(claims) & set(needed)):
            raise HTTPException(403, f"requires one of: {', '.join(needed)}")
        return claims

    return dependency
