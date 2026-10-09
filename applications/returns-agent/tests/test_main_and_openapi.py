import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))


def test_main_fails_closed_without_tenant(monkeypatch):
    monkeypatch.delenv("ENTRA_TENANT_ID", raising=False)
    sys.modules.pop("returns_agent.main", None)
    with pytest.raises(KeyError):
        importlib.import_module("returns_agent.main")


def test_main_builds_in_simulated_mode(monkeypatch):
    monkeypatch.setenv("ENTRA_TENANT_ID", "t")
    monkeypatch.setenv("API_AUDIENCE", "api://x")
    monkeypatch.setenv("MODEL_MODE", "simulated")
    sys.modules.pop("returns_agent.main", None)
    main = importlib.import_module("returns_agent.main")
    assert main.app.title == "Returns Resolution Agent"
    sys.modules.pop("returns_agent.main", None)


def test_openapi_export_has_operations_and_oauth():
    from export_openapi import export

    spec = export("returns.example.azurecontainerapps.io", "tenant", "client")
    ops = {op["operationId"] for p in spec["paths"].values() for op in p.values()}
    assert ops == {"resolveReturn", "decideReturn"}
    assert "entra" in spec["components"]["securitySchemes"]
    assert all(op["security"] for p in spec["paths"].values() for op in p.values())
