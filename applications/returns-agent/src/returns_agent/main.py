"""Container entrypoint. Configuration comes from environment variables (set by Terraform)."""

import logging
import os

from retail_ai.agents import openai_llm
from retail_ai.identity import get_credential, get_token_provider
from retail_ai.integrations import ApiClient
from retail_ai.models import get_openai_client
from retail_ai.observability import configure_azure_monitor, configure_logging
from retail_ai.service import EntraTokenValidator

from returns_agent.app import create_app
from returns_agent.simulated import SimulatedEnterprise
from returns_agent.simulated_model import rejected_aware_llm
from returns_agent.tools import SYSTEM_PROMPT, TOOL_SPECS


def build():
    configure_logging()
    configure_azure_monitor(os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"))
    validator = EntraTokenValidator(os.environ["ENTRA_TENANT_ID"], os.environ["API_AUDIENCE"].split(","))  # fail closed

    if os.environ.get("MODEL_MODE", "azure") == "simulated":
        llm = rejected_aware_llm
    else:  # Foundry-managed Azure OpenAI deployment
        credential = get_credential()
        client = get_openai_client(os.environ["AZURE_OPENAI_ENDPOINT"], credential=credential)
        llm = openai_llm(client, os.environ["AZURE_OPENAI_DEPLOYMENT"], TOOL_SPECS, SYSTEM_PROMPT)

    if os.environ.get("ENTERPRISE_API_MODE", "simulated") == "simulated":
        api = ApiClient("http://enterprise.sim", transport=SimulatedEnterprise().transport())
    else:
        base = os.environ["ENTERPRISE_API_BASE_URL"]
        api = ApiClient(base, token_provider=get_token_provider(os.environ["ENTERPRISE_API_SCOPE"]))
    logging.getLogger(__name__).info("returns agent starting")
    return create_app(validator, llm, api)


app = build()
