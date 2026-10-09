"""Offline quality/safety gate (runs in CI). The same cases feed Foundry evaluation in deployed environments."""

import json
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from retail_ai.evaluation import Case, contains, no_pii, no_prompt_injection_leak, run_eval
from retail_ai.integrations import ApiClient
from retail_ai.service import EntraTokenValidator
from returns_agent.app import create_app
from returns_agent.simulated import SimulatedEnterprise
from returns_agent.simulated_model import rejected_aware_llm

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
CASES = [json.loads(line) for line in (Path(__file__).parents[1] / "evals/cases.jsonl").read_text().splitlines()]


def test_returns_agent_quality_and_safety():
    validator = EntraTokenValidator("t", "aud", key_resolver=lambda t: KEY.public_key())
    api = ApiClient("http://sim", transport=SimulatedEnterprise().transport())
    client = TestClient(create_app(validator, rejected_aware_llm, api))
    tok = jwt.encode({"iss": "https://login.microsoftonline.com/t/v2.0", "aud": "aud",
                      "exp": time.time() + 300, "roles": ["Returns.Resolve", "Returns.Approve"]},
                     KEY, algorithm="RS256")
    h = {"Authorization": f"Bearer {tok}"}

    def agent(case: Case) -> str:
        r = client.post("/v1/returns/resolve", json={"message": case.input}, headers=h).json()
        if r["status"] == "awaiting_approval":
            r = client.post(f"/v1/returns/{r['thread_id']}/decision",
                            json={"approved": True, "reviewer": "eval"}, headers=h).json()
        return r["reply"]

    cases = [Case(c["expected"], c["query"], [c["context"]]) for c in CASES]
    expected = {c["expected"]: contains({"refund": "refund has been issued", "repair": "repair has been booked",
                                         "outside": "outside"}[c["expected"]]) for c in CASES}

    def matches_expected(case, output):
        return expected[case.name](case, output)

    run_eval(agent, cases, [matches_expected, no_pii, no_prompt_injection_leak()]).assert_pass()
