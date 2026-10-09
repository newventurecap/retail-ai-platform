# Plan: Foundations

Goal: a versioned, tested platform package (`retail_ai`) that applications can pin and build on. No applications yet.

Principles: thin slices, each independently testable; reuse patterns, not runtime or data stores; every module ships with tests, all run against mocks (no live Azure needed); semver tags at the end of each phase.

## Phase 0: Scaffold (done)
- Repo, structure, README, `pyproject.toml` (`platform/` imported as `retail_ai`).
- `models`: Azure OpenAI client (Entra auth, retries) + test.

## Phase 1: Core access (v0.2.0)
- `identity`: single place for Entra credentials (managed identity in Azure, developer login locally); `models` consumes it.
- `observability`: structured logging, OpenTelemetry tracing, token/latency metrics; wrap `models` calls.
- Lint and tests run locally (`ruff`, `pytest`); GitHub is only the repository, no workflows.
- Done when: a call through `models` produces a trace and local lint/tests pass.

## Phase 2: Knowledge and integrations (v0.3.0)
- `retrieval`: document ingestion, chunking, AI Search indexing, permission-aware retrieval. Index is per application, never shared by default.
- `integrations`: base API client (auth, retries, timeouts, logging) plus a mock-server test harness.
- Done when: a sample document set can be ingested and queried, and a mock API called, both from tests.

## Phase 3: Agent runtime (v0.4.0)
- `agents`: LangGraph templates (state, tool registry, error handling).
- Human-approval step as a reusable node (pause, resume, audit record).
- Done when: a toy agent runs end to end with a tool call and an approval gate.

## Phase 4: Evaluation and governance (v0.5.0)
- `evaluation`: quality and safety test harness (golden sets, groundedness, prompt-injection and PII checks); runs locally with `pytest`.
- Governance: tool allow-lists, audit logging of consequential actions, content-safety hooks.
- Done when: tests fail on a deliberate quality or safety regression.

## Phase 5: Infrastructure (v0.6.0)
- `infrastructure/terraform`: modules for Foundry/OpenAI, AI Search, Key Vault, Entra app registrations/RBAC, monitoring (App Insights, alerts, dashboards).
- Per-application environments consume modules via config only.
- Deployment is manual (see `docs/deployment.md`).
- Done when: a fresh environment deploys from scratch with one pipeline run.

## Phase 6: Release as v1.0.0
- API review of all modules, docs for application authors, an application template.
- Document how a Copilot Studio front end calls a Python agent (Copilot Studio stays thin; logic lives in the Python code).
- Done when: a new application can be started from the template using only the published package.

## After v1.0.0
Applications (`returns-agent`, `sales-agent`) are built in their own phases on the pinned package.

## Demo track: Returns agent on Azure
Scope: deploy the Python backend to Azure Container Apps, expose Entra-authenticated APIs, connect Copilot Studio, use Azure AI Foundry for model configuration and evaluation, and Application Insights for operations. Synthetic data and simulated enterprise APIs.
- `platform/service` (Entra token validation), `applications/returns-agent` (API, tools, simulated APIs, Dockerfile, eval cases).
- Terraform: Container Apps, ACR, Foundry hub/project, Entra API registration, on top of the Phase 5 modules.
- `docs/deployment.md` (manual Terraform apply, build, roll out, smoke test), `docs/copilot-studio.md`.

Status: phases 1-6 and the demo track are implemented and verified locally (ruff, 46 mocked tests, `terraform validate`). Not verified against real Azure: no deployment, no live Foundry evaluation, no Copilot Studio connector run, no Docker image build (Docker is not installed on this machine).

## Design decisions
- Testing is by mocking (fake Azure OpenAI, AI Search, Entra and business APIs), so tests need no Azure subscription.
- Copilot Studio has limited extensibility, so it is only a front end. The agent logic, tools and integrations live in this Python package.

## Open risks
- Untested against live Azure: Foundry resource arguments, Container Apps ingress/auth behaviour and the Copilot Studio connector flow need a first real deployment to confirm.
- Mocks can drift from real Azure behaviour. Mitigation: keep mocks at the SDK boundary and add a few opt-in live smoke tests later, once a subscription is available.
- Approval is a separate role (`Returns.Approve`): the conversational API cannot approve its own refunds.
- Enterprise systems are reached only through `ApiClient`; the demo swaps in a simulated transport, so going live is configuration.
