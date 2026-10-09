"""OpenTelemetry helpers. Exporters are configured by the application, not here."""

from contextlib import contextmanager

from opentelemetry import trace

_TRACER_NAME = "retail_ai"


def get_tracer():
    return trace.get_tracer(_TRACER_NAME)


@contextmanager
def traced_span(name: str, **attributes):
    """Span that records the exception and re-raises."""
    with get_tracer().start_as_current_span(name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        yield span


def record_llm_usage(span, response) -> None:
    """Attach token usage (OpenAI-style ``response.usage``) to a span."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    span.set_attribute("gen_ai.usage.input_tokens", usage.prompt_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", usage.completion_tokens)


def configure_azure_monitor(connection_string: str | None, *, configure=None) -> bool:
    """Send traces/logs/metrics to Application Insights. No-op without a connection string.

    Requires the ``azure`` extra (azure-monitor-opentelemetry). ``configure`` is injectable for tests.
    """
    if not connection_string:
        return False
    if configure is None:
        from azure.monitor.opentelemetry import configure_azure_monitor as configure
    configure(connection_string=connection_string)
    return True
