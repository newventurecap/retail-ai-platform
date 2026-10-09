"""HTTP API for the Returns agent. Copilot Studio calls these endpoints via a custom connector."""

import uuid

from fastapi import Depends, FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field
from retail_ai.agents import AuditLog, build_agent
from retail_ai.integrations import ApiClient
from retail_ai.service import EntraTokenValidator, require_roles

from returns_agent.tools import build_registry

RESOLVE_ROLE = "Returns.Resolve"
APPROVE_ROLE = "Returns.Approve"


class ResolveRequest(BaseModel):
    message: str = Field(description="Customer message, e.g. 'I want to return order ORD-1001'")
    thread_id: str | None = Field(default=None, description="Pass back to continue a conversation")


class DecisionRequest(BaseModel):
    approved: bool
    reviewer: str = Field(description="Name or id of the human reviewer")


class AgentResponse(BaseModel):
    thread_id: str
    status: str = Field(description="'completed' or 'awaiting_approval'")
    reply: str | None = None
    pending_action: dict | None = None


def create_app(validator: EntraTokenValidator, llm, api: ApiClient, audit: AuditLog | None = None) -> FastAPI:
    audit = audit or AuditLog()
    agent = build_agent(llm, build_registry(api), audit)
    app = FastAPI(title="Returns Resolution Agent", version="0.1.0")
    app.state.audit = audit

    def respond(thread_id: str, result: dict) -> AgentResponse:
        if "__interrupt__" in result:
            action = result["__interrupt__"][0].value["approve_tool"]
            return AgentResponse(thread_id=thread_id, status="awaiting_approval", pending_action=action,
                                 reply="This action needs a human reviewer's approval.")
        return AgentResponse(thread_id=thread_id, status="completed",
                             reply=result["messages"][-1].get("content"))

    @app.get("/healthz", include_in_schema=False)
    def health():
        return {"status": "ok"}

    @app.post("/v1/returns/resolve", operation_id="resolveReturn", response_model=AgentResponse,
              summary="Start or continue a returns conversation")
    def resolve(req: ResolveRequest, claims: dict = Depends(require_roles(validator, RESOLVE_ROLE))):
        thread_id = req.thread_id or str(uuid.uuid4())
        cfg = {"configurable": {"thread_id": thread_id}}
        result = agent.invoke({"messages": [{"role": "user", "content": req.message}], "pending": None}, cfg)
        return respond(thread_id, result)

    @app.post("/v1/returns/{thread_id}/decision", operation_id="decideReturn", response_model=AgentResponse,
              summary="Approve or reject a pending refund/repair")
    def decide(thread_id: str, req: DecisionRequest,
               claims: dict = Depends(require_roles(validator, APPROVE_ROLE))):
        cfg = {"configurable": {"thread_id": thread_id}}
        if not agent.get_state(cfg).next:
            raise HTTPException(409, "no pending approval for this thread")
        result = agent.invoke(Command(resume={"approved": req.approved, "reviewer": req.reviewer}), cfg)
        return respond(thread_id, result)

    return app
