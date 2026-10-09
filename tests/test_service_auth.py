import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from retail_ai.service import AuthError, EntraTokenValidator, require_roles

TENANT, AUD = "tenant-1", "api://retail"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(key=KEY, **over):
    claims = {"iss": f"https://login.microsoftonline.com/{TENANT}/v2.0", "aud": AUD,
              "exp": time.time() + 300, "roles": ["Returns.Resolve"], **over}
    return jwt.encode(claims, key, algorithm="RS256")


validator = EntraTokenValidator(TENANT, AUD, key_resolver=lambda t: KEY.public_key())
app = FastAPI()


@app.get("/r", dependencies=[Depends(require_roles(validator, "Returns.Resolve"))])
def r():
    return {"ok": True}


@app.get("/a")
def a(claims=Depends(require_roles(validator, "Returns.Approve"))):
    return claims["roles"]


client = TestClient(app)


def get(path, tok=None):
    return client.get(path, headers={"Authorization": f"Bearer {tok}"} if tok else {})


def test_valid_token_accepted():
    assert get("/r", token()).status_code == 200


def test_missing_token_401():
    assert get("/r").status_code == 401


@pytest.mark.parametrize("bad", [
    token(exp=time.time() - 10), token(aud="api://other"), token(iss="https://evil/"), token(OTHER),
])
def test_bad_tokens_401(bad):
    assert get("/r", bad).status_code == 401


def test_wrong_role_403_and_scope_accepted():
    assert get("/a", token()).status_code == 403
    assert get("/a", token(roles=[], scp="Returns.Approve")).status_code == 200


def test_validator_rejects_missing_config():
    with pytest.raises(ValueError):
        EntraTokenValidator("", AUD)
    with pytest.raises(AuthError):
        validator.validate("garbage")
