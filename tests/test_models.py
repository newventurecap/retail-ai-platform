from unittest.mock import MagicMock

from retail_ai.models import get_openai_client


def test_client_uses_endpoint_and_retries():
    client = get_openai_client("https://example.openai.azure.com", credential=MagicMock())
    assert str(client.base_url).startswith("https://example.openai.azure.com")
    assert client.max_retries == 5
