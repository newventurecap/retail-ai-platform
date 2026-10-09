"""Simulated enterprise APIs (orders, policies, CRM) backed by synthetic data.

Exposed as an httpx transport so the real ``ApiClient`` code path is exercised; pointing the app
at the real systems later only means changing the base URLs and dropping this transport.
"""

import json
from importlib import resources

import httpx


def _load(name: str) -> dict:
    return json.loads(resources.files("returns_agent.data").joinpath(name).read_text())


class SimulatedEnterprise:
    def __init__(self):
        self.orders = _load("orders.json")
        self.policies = _load("policies.json")
        self.crm_cases: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        parts = request.url.path.strip("/").split("/")
        if request.method == "GET" and parts[0] == "orders" and len(parts) == 2:
            order = self.orders.get(parts[1])
            return httpx.Response(200, json={"order_id": parts[1], **order}) if order else httpx.Response(
                404, json={"error": "order not found"})
        if request.method == "GET" and parts[0] == "policies" and len(parts) == 2:
            policy = self.policies.get(parts[1])
            return httpx.Response(200, json={"category": parts[1], **policy}) if policy else httpx.Response(
                404, json={"error": "policy not found"})
        if request.method == "POST" and parts == ["crm", "cases"]:
            case = {"case_id": f"CASE-{len(self.crm_cases) + 1:04d}", **json.loads(request.content)}
            self.crm_cases.append(case)
            return httpx.Response(201, json=case)
        return httpx.Response(404, json={"error": "not found"})

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)
