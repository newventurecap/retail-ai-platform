# Deploying the Returns agent demo to Azure

The demo runs on **synthetic data and simulated enterprise APIs** (orders, policies, CRM). The model is the
Azure OpenAI deployment managed in **Azure AI Foundry** (`MODEL_MODE=azure`), or a deterministic stand-in
(`MODEL_MODE=simulated`) when no model quota is available.

## What gets created (`infrastructure/terraform/environments/example`)
| Piece | Purpose |
|---|---|
| Container Apps environment + app | Hosts the Python API (port 8000, `/healthz` probes, 1-3 replicas) |
| Container Registry | Image store; Container App pulls with its managed identity (no admin user) |
| User-assigned managed identity | The agent's own identity: AcrPull, OpenAI User, Search Reader, Key Vault Secrets User |
| Entra app registration | API audience, delegated scope `Returns.Resolve`, app roles `Returns.Resolve` / `Returns.Approve` |
| Azure OpenAI + Foundry hub/project | Model deployments (`chat`), model configuration, evaluation runs; key auth disabled |
| Log Analytics + Application Insights + alert | Container logs, OpenTelemetry traces/metrics, failed-request alert |
| Key Vault, AI Search | Secrets and (later) the knowledge index |

## Steps
1. One-time: create a GitHub OIDC app registration for the pipeline; set repository variables `AZURE_CLIENT_ID`,
   `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`; create a GitHub Environment `example` with required reviewers.
2. Run the **Deploy** workflow (`workflow_dispatch`). It applies Terraform, runs the lint + test + eval gate,
   builds and pushes the image, rolls out a new revision, and smoke-tests (health OK, anonymous call returns 401).
3. Grant users the app roles on the enterprise application: `Returns.Resolve` for agent users,
   `Returns.Approve` for reviewers only.
4. Generate the connector spec and connect Copilot Studio (see `copilot-studio.md`).

## Authentication
Every `/v1/*` call needs an Entra bearer token for this API (signature, issuer, audience and expiry are checked;
the service refuses to start without `ENTRA_TENANT_ID` and `API_AUDIENCE`). `resolveReturn` requires
`Returns.Resolve`; `decideReturn` requires `Returns.Approve`, so the conversational agent cannot approve its own actions.

## Operations
- Traces and metrics: Application Insights (`APPLICATIONINSIGHTS_CONNECTION_STRING` injected as a secret).
- Audit events (`retail_ai.audit` logger: approvals with reviewer, tool calls, blocked tools) land in Log Analytics.
- Evaluation: CI runs `applications/returns-agent/tests/test_evals.py`. In Foundry, run
  `retail_ai.evaluation.foundry.run_foundry_evaluation("applications/returns-agent/evals/cases.jsonl", ...)`
  with `pip install ".[foundry]"` to record results in the Foundry project.

## Moving beyond the demo
Set `ENTERPRISE_API_MODE=real` with `ENTERPRISE_API_BASE_URL` and `ENTERPRISE_API_SCOPE`; the same `ApiClient`
code path is used, so only configuration changes.
