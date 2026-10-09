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

## Steps (run from your machine; nothing runs on GitHub)
1. Sign in: `az login`, then pick the subscription.
2. Infrastructure: `cd infrastructure/terraform/environments/example && terraform init && terraform apply`.
3. Quality gate: `pip install -e ".[dev]" -e applications/returns-agent && ruff check . && pytest -q`.
4. Build and push the image (from the repository root; use the `acr_login_server` output):
   `az acr build -r <acr-name> -t returns-agent:v1 -f applications/returns-agent/Dockerfile .`
5. Roll out: `az containerapp update -g <resource_group> -n <container_app_name> --image <acr_login_server>/returns-agent:v1`
6. Smoke test: `curl <api_url>/healthz` returns OK, and an anonymous `POST /v1/returns/resolve` returns 401.
7. Grant users the app roles on the enterprise application: `Returns.Resolve` for agent users,
   `Returns.Approve` for reviewers only.
8. Generate the connector spec and connect Copilot Studio (see `copilot-studio.md`).

## Authentication
Every `/v1/*` call needs an Entra bearer token for this API (signature, issuer, audience and expiry are checked;
the service refuses to start without `ENTRA_TENANT_ID` and `API_AUDIENCE`). `resolveReturn` requires
`Returns.Resolve`; `decideReturn` requires `Returns.Approve`, so the conversational agent cannot approve its own actions.

## Operations
- Traces and metrics: Application Insights (`APPLICATIONINSIGHTS_CONNECTION_STRING` injected as a secret).
- Audit events (`retail_ai.audit` logger: approvals with reviewer, tool calls, blocked tools) land in Log Analytics.
- Evaluation: run `pytest` (includes `applications/returns-agent/tests/test_evals.py`) before each rollout. In Foundry, run
  `retail_ai.evaluation.foundry.run_foundry_evaluation("applications/returns-agent/evals/cases.jsonl", ...)`
  with `pip install ".[foundry]"` to record results in the Foundry project.

## Moving beyond the demo
Set `ENTERPRISE_API_MODE=real` with `ENTERPRISE_API_BASE_URL` and `ENTERPRISE_API_SCOPE`; the same `ApiClient`
code path is used, so only configuration changes.
