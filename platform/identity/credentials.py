"""Entra ID credentials: one place decides how the platform authenticates."""

import os

from azure.identity import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)

COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
SEARCH_SCOPE = "https://search.azure.com/.default"


def get_credential(*, managed_identity_client_id: str | None = None):
    """Return the credential for the current environment.

    A user-assigned managed identity is used when a client id is given (or set in
    ``AZURE_MANAGED_IDENTITY_CLIENT_ID``), so each application keeps its own identity.
    Otherwise falls back to ``DefaultAzureCredential`` (developer login, workload identity, ...).
    """
    client_id = managed_identity_client_id or os.environ.get("AZURE_MANAGED_IDENTITY_CLIENT_ID")
    if client_id:
        return ManagedIdentityCredential(client_id=client_id)
    return DefaultAzureCredential()


def get_token_provider(scope: str, credential=None):
    """Callable returning a fresh bearer token for ``scope``."""
    return get_bearer_token_provider(credential or get_credential(), scope)
