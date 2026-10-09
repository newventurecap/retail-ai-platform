from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from retail_ai.identity import get_credential


def test_default_credential(monkeypatch):
    monkeypatch.delenv("AZURE_MANAGED_IDENTITY_CLIENT_ID", raising=False)
    assert isinstance(get_credential(), DefaultAzureCredential)


def test_managed_identity_when_client_id_given():
    assert isinstance(get_credential(managed_identity_client_id="abc"), ManagedIdentityCredential)


def test_managed_identity_from_env(monkeypatch):
    monkeypatch.setenv("AZURE_MANAGED_IDENTITY_CLIENT_ID", "abc")
    assert isinstance(get_credential(), ManagedIdentityCredential)
