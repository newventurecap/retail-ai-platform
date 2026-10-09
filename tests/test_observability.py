import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from retail_ai.models import chat
from retail_ai.observability import JsonFormatter, traced_span


def test_json_formatter_includes_extra_fields():
    record = logging.LogRecord("x", logging.INFO, "f", 1, "hello %s", ("w",), None)
    record.order_id = 7
    out = json.loads(JsonFormatter().format(record))
    assert out["message"] == "hello w" and out["order_id"] == 7 and out["level"] == "INFO"


def test_span_records_exception(spans):
    with pytest.raises(ValueError):
        with traced_span("boom"):
            raise ValueError("x")
    assert spans.get_finished_spans()[0].status.status_code.name == "ERROR"


def test_chat_emits_trace_with_token_usage(spans):
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=5)
    )
    chat(client, "gpt-4o", [{"role": "user", "content": "hi"}])
    span = spans.get_finished_spans()[0]
    assert span.name == "llm.chat"
    assert span.attributes["gen_ai.usage.input_tokens"] == 11
    assert span.attributes["gen_ai.usage.output_tokens"] == 5
