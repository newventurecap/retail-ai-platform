"""LangGraph agent template: model step -> (optional human approval) -> tool step -> loop.

``llm`` is any callable ``(messages) -> {"content": str}`` or ``{"tool_call": {"name", "args"}}``,
which keeps the template independent of a specific model SDK.
Approval uses LangGraph ``interrupt``; a checkpointer is required to pause and resume.
"""

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from retail_ai.agents.audit import AuditLog
from retail_ai.agents.tools import ToolNotAllowed, ToolRegistry


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    pending: dict | None


def build_agent(llm, registry: ToolRegistry, audit: AuditLog | None = None, *, checkpointer=None,
                max_steps: int = 10):
    audit = audit or AuditLog()

    def model_node(state: AgentState):
        if sum(m["role"] == "assistant" for m in state["messages"]) >= max_steps:
            return {"messages": [{"role": "assistant", "content": "Step limit reached."}], "pending": None}
        out = llm(state["messages"])
        if "tool_call" in out:
            call = out["tool_call"]
            return {"messages": [{"role": "assistant", "tool_call": call}], "pending": call}
        return {"messages": [{"role": "assistant", "content": out["content"]}], "pending": None}

    def tool_node(state: AgentState):
        call = state["pending"]
        try:
            tool = registry.get(call["name"])
        except ToolNotAllowed as e:
            audit.record("tool_blocked", tool=call["name"])
            return {"messages": [{"role": "tool", "content": str(e)}], "pending": None}
        if tool.requires_approval:
            decision = interrupt({"approve_tool": call})
            approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)
            reviewer = decision.get("reviewer") if isinstance(decision, dict) else None
            audit.record("approval", tool=call["name"], args=call["args"], approved=approved,
                         reviewer=reviewer)
            if not approved:
                return {"messages": [{"role": "tool", "content": "Action rejected by reviewer."}],
                        "pending": None}
        result = tool.fn(**call["args"])
        audit.record("tool_call", tool=call["name"], args=call["args"])
        return {"messages": [{"role": "tool", "content": str(result)}], "pending": None}

    def after_model(state: AgentState):
        return "tools" if state["pending"] else END

    graph = StateGraph(AgentState)
    graph.add_node("model", model_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", after_model, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")
    return graph.compile(checkpointer=checkpointer or MemorySaver())
