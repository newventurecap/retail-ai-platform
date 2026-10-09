# Azure AI Foundry hub + project: model configuration, evaluation runs and traces live here.
variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "key_vault_id" { type = string }
variable "application_insights_id" { type = string }
variable "openai_account_id" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

data "azurerm_client_config" "current" {}

resource "azurerm_storage_account" "this" {
  name                            = substr(replace("${var.name}foundry", "-", ""), 0, 24)
  location                        = var.location
  resource_group_name             = var.resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  tags                            = var.tags
}

resource "azurerm_ai_foundry" "hub" {
  name                    = "${var.name}-hub"
  location                = var.location
  resource_group_name     = var.resource_group_name
  storage_account_id      = azurerm_storage_account.this.id
  key_vault_id            = var.key_vault_id
  application_insights_id = var.application_insights_id
  identity {
    type = "SystemAssigned"
  }
  tags = var.tags
}

resource "azurerm_ai_foundry_project" "this" {
  name               = "${var.name}-project"
  location           = var.location
  ai_services_hub_id = azurerm_ai_foundry.hub.id
  identity {
    type = "SystemAssigned"
  }
  tags = var.tags
}

# Let the hub use the Azure OpenAI account's deployments.
resource "azurerm_role_assignment" "hub_openai" {
  scope                = var.openai_account_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_ai_foundry.hub.identity[0].principal_id
}

output "project_id" { value = azurerm_ai_foundry_project.this.id }
output "project_name" { value = azurerm_ai_foundry_project.this.name }
