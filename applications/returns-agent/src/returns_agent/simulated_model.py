"""Deterministic stand-in for the model, used for the synthetic-data demo and offline tests.

Follows the same contract as the Azure OpenAI adapter so the rest of the stack is unchanged.
"""

import json
import re


def simulated_llm(messages: list[dict]) -> dict:
    tools = [m for m in messages if m["role"] == "tool"]
    calls = [m["tool_call"] for m in messages if "tool_call" in m]
    user_text = " ".join(m["content"] for m in messages if m["role"] == "user")
    match = re.search(r"ORD-\d+", user_text)
    if not tools:
        if not match:
            return {"content": "Please give me your order number (for example ORD-1001)."}
        return {"tool_call": {"name": "get_order", "args": {"order_id": match.group()}}}

    last, last_call = tools[-1]["content"], calls[-1]["name"]
    if last_call == "get_order":
        data = json.loads(last)
        if "error" in data:
            return {"content": "I could not find that order."}
        return {"tool_call": {"name": "check_eligibility", "args": {"order_id": data["order_id"]}}}
    if last_call == "check_eligibility":
        e = json.loads(last)
        if e["resolution"] == "refund":
            return {"tool_call": {"name": "issue_refund",
                                  "args": {"order_id": e["order_id"], "amount": e["amount"]}}}
        if e["resolution"] == "repair":
            return {"tool_call": {"name": "arrange_repair", "args": {"order_id": e["order_id"]}}}
        return {"tool_call": {"name": "record_resolution",
                              "args": {"order_id": e["order_id"], "resolution": "not eligible"}}}
    if last_call in ("issue_refund", "arrange_repair"):
        done = "refund" if last_call == "issue_refund" else "repair"
        return {"tool_call": {"name": "record_resolution",
                              "args": {"order_id": calls[-1]["args"]["order_id"], "resolution": done}}}
    if last_call == "record_resolution":
        case = json.loads(last)
        outcome = {"refund": "A refund has been issued.", "repair": "A warranty repair has been booked.",
                   "not eligible": "This order is outside the return and warranty periods."}[case["resolution"]]
        return {"content": f"{outcome} Reference {case['case_id']}."}
    return {"content": "Done."}


def rejected_aware_llm(messages: list[dict]) -> dict:
    """Wraps ``simulated_llm``: if a reviewer rejected the action, escalate instead of recording success."""
    last = messages[-1]
    if last["role"] == "tool" and last["content"].startswith("Action rejected"):
        return {"content": "A reviewer declined this action, so it has been escalated to a human agent."}
    return simulated_llm(messages)
