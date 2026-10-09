"""Returns-specific tools. Business logic lives here; the platform supplies the plumbing."""

import json

from retail_ai.agents import ToolRegistry
from retail_ai.integrations import ApiClient, ApiError


def build_registry(api: ApiClient) -> ToolRegistry:
    def get_order(order_id: str) -> str:
        try:
            return json.dumps(api.get(f"/orders/{order_id}"))
        except ApiError as e:
            return json.dumps({"error": str(e)})

    def check_eligibility(order_id: str) -> str:
        order = api.get(f"/orders/{order_id}")
        policy = api.get(f"/policies/{order['category']}")
        days = order["days_since_purchase"]
        if days <= policy["return_window_days"]:
            resolution = "refund"
        elif days <= policy["warranty_days"]:
            resolution = "repair"
        else:
            resolution = "none"
        return json.dumps({"order_id": order_id, "resolution": resolution, "amount": order["price"],
                           "days_since_purchase": days, "policy": policy})

    def issue_refund(order_id: str, amount: float) -> str:
        return json.dumps({"order_id": order_id, "refunded": amount})

    def arrange_repair(order_id: str) -> str:
        return json.dumps({"order_id": order_id, "repair": "booked"})

    def record_resolution(order_id: str, resolution: str) -> str:
        return json.dumps(api.post("/crm/cases", json={"order_id": order_id, "resolution": resolution}))

    reg = ToolRegistry()
    reg.register("get_order", get_order)
    reg.register("check_eligibility", check_eligibility)
    reg.register("issue_refund", issue_refund, requires_approval=True)      # consequential
    reg.register("arrange_repair", arrange_repair, requires_approval=True)  # consequential
    reg.register("record_resolution", record_resolution)
    return reg


TOOL_SPECS = [
    {"name": "get_order", "description": "Retrieve a customer order by id.",
     "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "check_eligibility",
     "description": "Apply returns/warranty policy: returns refund, repair or none for an order.",
     "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "issue_refund", "description": "Refund an order (requires human approval).",
     "parameters": {"type": "object", "properties": {"order_id": {"type": "string"},
                                                       "amount": {"type": "number"}},
                    "required": ["order_id", "amount"]}},
    {"name": "arrange_repair", "description": "Book a warranty repair (requires human approval).",
     "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "record_resolution", "description": "Record the final resolution in the CRM.",
     "parameters": {"type": "object", "properties": {"order_id": {"type": "string"},
                                                       "resolution": {"type": "string"}},
                    "required": ["order_id", "resolution"]}},
]

SYSTEM_PROMPT = (
    "You are a retail Returns Resolution Agent. Look up the order, check eligibility with the policy "
    "tool, then act: refund, repair, or explain why neither applies. Refunds and repairs need human "
    "approval; after any outcome, record the resolution in the CRM. Never invent order data."
)
