# Retail AI Platform

A shared platform for building retail AI agents on Azure, plus the applications built on top of it.

Each application reuses the common platform (models, identity, retrieval, agent runtime, integrations, observability, evaluation) and adds only its own business logic and tools.

## Technology

Azure AI Foundry, Azure OpenAI, Copilot Studio, Python, agents, integration, CI/CD, security, governance and production monitoring.

## Applications

### Returns Resolution Agent (`applications/returns-agent`)

- Retrieve customer orders.
- Interpret returns and warranty policies.
- Check product and purchase eligibility.
- Recommend repair, refund or replacement.
- Request human approval before consequential actions.
- Record the resolution in CRM.

### Sales Assistant (`applications/sales-agent`)

- Retrieve product specifications.
- Check store and warehouse availability.
- Compare products against customer requirements.
- Suggest alternatives.
- Retrieve current pricing and delivery options.
- Reserve an item through an approved API.

## What is reusable

| Component | Build once | Per new use case |
|---|---|---|
| Azure infrastructure | Terraform modules | Configuration |
| Model access | Shared client, authentication, retries | Model selection |
| Agent framework | LangGraph templates | Tools and workflow |
| RAG pipeline | Ingestion, indexing, retrieval | Documents and permissions |
| API integration | Auth, retries, logging | Business endpoints |
| Security | Entra ID, Key Vault, RBAC | Access policies |
| Monitoring | Tracing, alerts, dashboards | Business KPIs |
| CI/CD | Build, test, deploy pipeline | Evaluation tests |

The reuse is in the engineering patterns, not necessarily in sharing every runtime or data store. For example, the Returns Agent and Sales Agent can share model access and monitoring patterns while having separate identities, permissions, knowledge indexes and deployment boundaries.

## Structure

```
retail-ai-platform/
├── platform/
│   ├── models/          # Azure OpenAI clients
│   ├── identity/        # Entra authentication
│   ├── retrieval/       # AI Search / RAG
│   ├── agents/          # LangGraph runtime
│   ├── integrations/    # API client framework
│   ├── observability/   # Tracing, metrics
│   └── evaluation/      # Quality and safety tests
│
├── applications/
│   ├── returns-agent/
│   └── sales-agent/
│
├── infrastructure/
│   └── terraform/
│
└── .github/workflows/
```

## Layout

- **platform/**: reusable building blocks shared by every application.
- **applications/**: individual agents that consume the platform.
- **infrastructure/**: Terraform for the Azure resources.
- **.github/workflows/**: CI/CD pipelines.

## Getting started

The platform is a versioned Python package. The folder is `platform/` but it is imported as `retail_ai` (a top-level `platform` would shadow the standard library).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

```python
from retail_ai.models import get_openai_client
```

## Returns agent demo (synthetic data)

`applications/returns-agent` is a demo API built on the platform, using synthetic data and simulated enterprise APIs. It deploys to Azure Container Apps, authenticates callers with Entra ID and connects to Copilot Studio.

- Deployment: [docs/deployment.md](docs/deployment.md)
- Copilot Studio connector: [docs/copilot-studio.md](docs/copilot-studio.md)
- Delivery plan and status: [PLAN.md](PLAN.md)
