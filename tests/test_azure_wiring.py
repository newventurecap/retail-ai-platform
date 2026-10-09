import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from retail_ai.agents import openai_llm
from retail_ai.evaluation.foundry import run_foundry_evaluation
from retail_ai.observability import configure_azure_monitor


def test_azure_monitor_noop_without_connection_string():
    configure = MagicMock()
    assert configure_azure_monitor(None, configure=configure) is False
    assert configure_azure_monitor("InstrumentationKey=x", configure=configure) is True
    configure.assert_called_once_with(connection_string="InstrumentationKey=x")


def test_foundry_evaluation_passes_project_and_evaluators():
    evaluate = MagicMock(return_value={"metrics": {}})
    run_foundry_evaluation("d.jsonl", project="https://p", model_config={}, evaluate=evaluate,
                           evaluators={"g": object()}, name="n")
    kw = evaluate.call_args.kwargs
    assert kw["data"] == "d.jsonl" and kw["azure_ai_project"] == "https://p"
    assert kw["evaluation_name"] == "n" and "g" in kw["evaluators"]


def _resp(msg):
    return SimpleNamespace(usage=None, choices=[SimpleNamespace(message=msg)])


def test_openai_llm_maps_tool_calls_and_text():
    client = MagicMock()
    fn = SimpleNamespace(name="get_order", arguments='{"order_id": "ORD-1"}')
    client.chat.completions.create.side_effect = [
        _resp(SimpleNamespace(tool_calls=[SimpleNamespace(function=fn)], content=None)),
        _resp(SimpleNamespace(tool_calls=None, content="hello")),
    ]
    llm = openai_llm(client, "chat", [{"name": "get_order", "description": "d", "parameters": {}}], "sys")
    assert llm([{"role": "user", "content": "hi"}]) == {
        "tool_call": {"name": "get_order", "args": {"order_id": "ORD-1"}}}
    history = [{"role": "user", "content": "hi"},
               {"role": "assistant", "tool_call": {"name": "get_order", "args": {"order_id": "ORD-1"}}},
               {"role": "tool", "content": json.dumps({"ok": 1})}]
    assert llm(history) == {"content": "hello"}
    sent = client.chat.completions.create.call_args.kwargs["messages"]
    assert sent[0]["role"] == "system" and sent[2]["tool_calls"][0]["id"] == "call_1"
    assert sent[3] == {"role": "tool", "tool_call_id": "call_1", "content": '{"ok": 1}'}
