import pytest
from langgraph.types import Command
from retail_ai.agents import AuditLog, ToolNotAllowed, ToolRegistry, build_agent


def scripted_llm(*steps):
    it = iter(steps)
    return lambda messages: next(it)


def run(agent, text, thread="t"):
    cfg = {"configurable": {"thread_id": thread}}
    return agent.invoke({"messages": [{"role": "user", "content": text}], "pending": None}, cfg), cfg


def test_tool_call_then_answer():
    reg = ToolRegistry()
    reg.register("lookup", lambda order_id: f"order {order_id}")
    llm = scripted_llm({"tool_call": {"name": "lookup", "args": {"order_id": 1}}}, {"content": "done"})
    result, _ = run(build_agent(llm, reg), "where is it?")
    assert result["messages"][-1]["content"] == "done"
    assert any(m.get("content") == "order 1" for m in result["messages"])


def test_unknown_tool_blocked_and_audited():
    audit = AuditLog()
    llm = scripted_llm({"tool_call": {"name": "delete_all", "args": {}}}, {"content": "ok"})
    run(build_agent(llm, ToolRegistry(), audit), "x")
    assert audit.events[0]["event"] == "tool_blocked"
    with pytest.raises(ToolNotAllowed):
        ToolRegistry().get("delete_all")


@pytest.mark.parametrize("approved", [True, False])
def test_approval_gate_pauses_and_resumes(approved):
    refunds = []
    reg = ToolRegistry()
    reg.register("refund", lambda amount: refunds.append(amount) or "refunded", requires_approval=True)
    audit = AuditLog()
    llm = scripted_llm({"tool_call": {"name": "refund", "args": {"amount": 50}}}, {"content": "finished"})
    agent = build_agent(llm, reg, audit)

    paused, cfg = run(agent, "refund me")
    assert "__interrupt__" in paused and refunds == []  # nothing executed before approval

    final = agent.invoke(Command(resume={"approved": approved}), cfg)
    assert final["messages"][-1]["content"] == "finished"
    assert refunds == ([50] if approved else [])
    assert audit.events[0] == {**audit.events[0], "event": "approval", "approved": approved}


def test_step_limit():
    reg = ToolRegistry()
    reg.register("noop", lambda: "x")
    llm = lambda messages: {"tool_call": {"name": "noop", "args": {}}}  # noqa: E731
    result, _ = run(build_agent(llm, reg, max_steps=3), "loop")
    assert result["messages"][-1]["content"] == "Step limit reached."
