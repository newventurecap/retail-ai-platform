# Entra app registration for the agent's API: delegated scope for Copilot Studio sign-in,
# and app roles so approvals can be restricted to reviewers.
terraform {
  required_providers {
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
  }
}

variable "display_name" { type = string }

resource "random_uuid" "scope" {}
resource "random_uuid" "role_resolve" {}
resource "random_uuid" "role_approve" {}

resource "azuread_application" "api" {
  display_name     = var.display_name
  sign_in_audience = "AzureADMyOrg"

  api {
    requested_access_token_version = 2
    oauth2_permission_scope {
      id                         = random_uuid.scope.result
      value                      = "Returns.Resolve"
      type                       = "User"
      admin_consent_display_name = "Resolve returns"
      admin_consent_description  = "Allows the app to resolve returns on behalf of the signed-in user"
      user_consent_display_name  = "Resolve returns"
      user_consent_description   = "Allows the app to resolve returns on your behalf"
    }
  }

  app_role {
    id                   = random_uuid.role_resolve.result
    value                = "Returns.Resolve"
    display_name         = "Returns Resolve"
    description          = "Submit returns conversations"
    allowed_member_types = ["User", "Application"]
  }

  app_role {
    id                   = random_uuid.role_approve.result
    value                = "Returns.Approve"
    display_name         = "Returns Approve"
    description          = "Approve or reject refunds and repairs"
    allowed_member_types = ["User"]
  }
}

resource "azuread_service_principal" "api" {
  client_id = azuread_application.api.client_id
}

output "client_id" { value = azuread_application.api.client_id }
output "audiences" { value = "${azuread_application.api.client_id},api://${azuread_application.api.client_id}" }
