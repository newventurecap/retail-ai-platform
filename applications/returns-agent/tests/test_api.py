import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from retail_ai.agents import AuditLog
from retail_ai.integrations import ApiClient
from retail_ai.service import EntraTokenValidator
from returns_agent.app import create_app
from returns_agent.simulated import SimulatedEnterprise
from returns_agent.simulated_model import rejected_aware_llm

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TENANT, AUD = "t1", "api://returns"


def token(*roles):
    return jwt.encode({"iss": f"https://login.microsoftonline.com/{TENANT}/v2.0", "aud": AUD,
                       "exp": time.time() + 300, "roles": list(roles)}, KEY, algorithm="RS256")


@pytest.fixture
def env():
    enterprise = SimulatedEnterprise()
    audit = AuditLog()
    validator = EntraTokenValidator(TENANT, AUD, key_resolver=lambda t: KEY.public_key())
    api = ApiClient("http://enterprise.sim", transport=enterprise.transport())
    client = TestClient(create_app(validator, rejected_aware_llm, api, audit))
    return client, enterprise, audit


def H(*roles):
    return {"Authorization": f"Bearer {token(*roles)}"}


def test_requires_auth(env):
    client, *_ = env
    assert client.post("/v1/returns/resolve", json={"message": "x"}).status_code == 401
    assert client.post("/v1/returns/resolve", json={"message": "x"}, headers=H("Other")).status_code == 403
    assert client.get("/healthz").status_code == 200


def test_missing_order_number_asks(env):
    client, *_ = env
    r = client.post("/v1/returns/resolve", json={"message": "I want to return something"},
                    headers=H("Returns.Resolve")).json()
    assert r["status"] == "completed" and "order number" in r["reply"]


def test_refund_flow_with_approval(env):
    client, enterprise, audit = env
    r = client.post("/v1/returns/resolve", json={"message": "Return order ORD-1001 please"},
                    headers=H("Returns.Resolve")).json()
    assert r["status"] == "awaiting_approval"
    assert r["pending_action"] == {"name": "issue_refund", "args": {"order_id": "ORD-1001", "amount": 1199.0}}
    assert enterprise.crm_cases == []  # nothing recorded before approval

    # the agent role cannot approve its own action
    assert client.post(f"/v1/returns/{r['thread_id']}/decision", json={"approved": True, "reviewer": "x"},
                       headers=H("Returns.Resolve")).status_code == 403

    done = client.post(f"/v1/returns/{r['thread_id']}/decision", json={"approved": True, "reviewer": "alice"},
                       headers=H("Returns.Approve")).json()
    assert done["status"] == "completed" and "refund has been issued" in done["reply"]
    assert enterprise.crm_cases[0]["resolution"] == "refund"
    assert any(e["event"] == "approval" and e["reviewer"] == "alice" for e in audit.events)


def test_rejection_escalates_without_crm_refund(env):
    client, enterprise, _ = env
    r = client.post("/v1/returns/resolve", json={"message": "Return ORD-1001"},
                    headers=H("Returns.Resolve")).json()
    done = client.post(f"/v1/returns/{r['thread_id']}/decision", json={"approved": False, "reviewer": "bob"},
                       headers=H("Returns.Approve")).json()
    assert "declined" in done["reply"] and enterprise.crm_cases == []


def test_warranty_repair_and_not_eligible(env):
    client, enterprise, _ = env
    r = client.post("/v1/returns/resolve", json={"message": "ORD-1002 is broken"},
                    headers=H("Returns.Resolve")).json()
    assert r["pending_action"]["name"] == "arrange_repair"  # 120 days: past 30-day return, within warranty
    r2 = client.post("/v1/returns/resolve", json={"message": "return ORD-1003"},
                     headers=H("Returns.Resolve")).json()
    assert r2["status"] == "completed" and "outside" in r2["reply"]
    assert enterprise.crm_cases[-1]["resolution"] == "not eligible"


def test_unknown_order_and_no_pending_decision(env):
    client, *_ = env
    r = client.post("/v1/returns/resolve", json={"message": "ORD-9999"}, headers=H("Returns.Resolve")).json()
    assert "could not find" in r["reply"]
    assert client.post(f"/v1/returns/{r['thread_id']}/decision", json={"approved": True, "reviewer": "a"},
                       headers=H("Returns.Approve")).status_code == 409
