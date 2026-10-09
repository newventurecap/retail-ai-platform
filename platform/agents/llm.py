"""Adapter from an Azure OpenAI deployment (configured in Azure AI Foundry) to the agent ``llm`` callable."""

import json

from retail_ai.models import chat


def openai_llm(client, deployment: str, tool_specs: list[dict], system_prompt: str = ""):
    """``tool_specs``: OpenAI function specs, ``{"name", "description", "parameters"}``."""
    tools = [{"type": "function", "function": spec} for spec in tool_specs]

    def to_openai(messages: list[dict]) -> list[dict]:
        out = [{"role": "system", "content": system_prompt}] if system_prompt else []
        call_id = 0
        for m in messages:
            if "tool_call" in m:
                call_id += 1
                call = m["tool_call"]
                out.append({"role": "assistant", "content": None, "tool_calls": [{
                    "id": f"call_{call_id}", "type": "function",
                    "function": {"name": call["name"], "arguments": json.dumps(call["args"])}}]})
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": f"call_{call_id}", "content": m["content"]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def llm(messages: list[dict]) -> dict:
        response = chat(client, deployment, to_openai(messages), tools=tools or None)
        msg = response.choices[0].message
        if getattr(msg, "tool_calls", None):
            call = msg.tool_calls[0].function
            return {"tool_call": {"name": call.name, "args": json.loads(call.arguments)}}
        return {"content": msg.content or ""}

    return llm
