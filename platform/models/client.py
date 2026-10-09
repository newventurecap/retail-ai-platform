"""Shared Azure OpenAI client: Entra ID auth (no API keys), retries, traced calls."""

from openai import AzureOpenAI
from retail_ai.identity import COGNITIVE_SCOPE, get_token_provider
from retail_ai.observability import record_llm_usage, traced_span


def get_openai_client(
    endpoint: str,
    *,
    api_version: str = "2024-10-21",
    credential=None,
    max_retries: int = 5,
    timeout: float = 60.0,
) -> AzureOpenAI:
    """Build an Azure OpenAI client authenticated with Entra ID.

    Model/deployment selection is left to the caller (per use case).
    """
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_version=api_version,
        azure_ad_token_provider=get_token_provider(COGNITIVE_SCOPE, credential),
        max_retries=max_retries,
        timeout=timeout,
    )


def chat(client, deployment: str, messages: list[dict], **kwargs):
    """Chat completion wrapped in a trace span with token usage."""
    with traced_span("llm.chat", **{"gen_ai.request.model": deployment}) as span:
        response = client.chat.completions.create(model=deployment, messages=messages, **kwargs)
        record_llm_usage(span, response)
        return response
