# Connecting Copilot Studio

Copilot Studio is the conversation front end. It has limited extensibility, so it holds no business logic: it
calls the two API operations below through a **custom connector**.

| Operation | Endpoint | Role needed | Used for |
|---|---|---|---|
| `resolveReturn` | `POST /v1/returns/resolve` | `Returns.Resolve` | Send the customer message; returns a reply, or `awaiting_approval` with the proposed action |
| `decideReturn` | `POST /v1/returns/{thread_id}/decision` | `Returns.Approve` | A human reviewer approves or rejects a refund/repair |

## Set up
1. Generate the spec with your values (host from the `api_url` output, tenant, `api_client_id` output):
   `python scripts/export_openapi.py <host> <tenant-id> <api-client-id> > returns-openapi.json`
   (`docs/returns-openapi.json` is a placeholder example.)
2. Power Apps / Power Automate -> **Custom connectors** -> import the OpenAPI file.
3. Security: **OAuth 2.0**, identity provider *Azure Active Directory*; client id/secret from a separate Entra app
   registration for the connector; scope `api://<api-client-id>/Returns.Resolve`. Add the connector's redirect URL
   to that registration and grant it permission to the API scope.
4. Copilot Studio -> your agent -> **Tools** -> add the connector actions.
5. In the topic: call `resolveReturn` with the user's message and store `thread_id`; if `status` is
   `awaiting_approval`, tell the user it is with a reviewer. Reviewers use `decideReturn` (a separate topic or
   Power Automate approval flow whose signed-in user holds `Returns.Approve`).

## Notes
- The connector must sign in as a real user (delegated). Reviewers need the `Returns.Approve` app role assigned.
- Keep `thread_id` between turns so the conversation continues.
