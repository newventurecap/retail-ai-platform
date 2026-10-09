"""Export the Returns API as an OpenAPI document for the Copilot Studio custom connector.

Usage: python scripts/export_openapi.py <api-host> <tenant-id> <api-client-id> > docs/returns-openapi.json
"""

import json
import sys

from retail_ai.integrations import ApiClient
from retail_ai.service import EntraTokenValidator
from returns_agent.app import create_app
from returns_agent.simulated import SimulatedEnterprise


def export(host: str, tenant: str, api_client_id: str) -> dict:
    validator = EntraTokenValidator(tenant, f"api://{api_client_id}", key_resolver=lambda t: None)
    api = ApiClient("http://sim", transport=SimulatedEnterprise().transport())
    spec = create_app(validator, lambda m: {"content": ""}, api).openapi()
    base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"
    scope = f"api://{api_client_id}/Returns.Resolve"
    spec["servers"] = [{"url": f"https://{host}"}]
    spec["components"]["securitySchemes"] = {
        "entra": {"type": "oauth2", "flows": {"authorizationCode": {
            "authorizationUrl": f"{base}/authorize", "tokenUrl": f"{base}/token",
            "scopes": {scope: "Resolve returns"}}}}
    }
    for path in spec["paths"].values():
        for op in path.values():
            op["security"] = [{"entra": [scope]}]
    return spec


if __name__ == "__main__":
    host, tenant, client_id = sys.argv[1:4]
    print(json.dumps(export(host, tenant, client_id), indent=2))
