variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "user_principal_ids" {
  type        = list(string)
  default     = []
  description = "Identities allowed to call the models (Cognitive Services OpenAI User)."
}
variable "deployments" {
  description = "Model deployments for this use case (model selection is per application)."
  type = map(object({
    model_name    = string
    model_version = string
    capacity      = number
  }))
}
variable "tags" {
  type    = map(string)
  default = {}
}

resource "azurerm_cognitive_account" "this" {
  name                          = "${var.name}-aoai"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "OpenAI"
  sku_name                      = "S0"
  custom_subdomain_name         = "${var.name}-aoai"
  local_auth_enabled            = false # Entra ID only, no API keys
  public_network_access_enabled = true
  tags                          = var.tags
}

resource "azurerm_cognitive_deployment" "this" {
  for_each             = var.deployments
  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.this.id
  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }
  sku {
    name     = "Standard"
    capacity = each.value.capacity
  }
}

resource "azurerm_role_assignment" "user" {
  for_each             = toset(var.user_principal_ids)
  scope                = azurerm_cognitive_account.this.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = each.value
}

output "endpoint" { value = azurerm_cognitive_account.this.endpoint }
output "id" { value = azurerm_cognitive_account.this.id }
