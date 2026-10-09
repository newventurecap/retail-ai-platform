# One application's environment (Returns agent demo). Copy per application; only configuration changes.
terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "azurerm" {
  features {}
}

variable "app_name" { default = "returns" }
variable "location" { default = "eastus2" }
variable "alert_email" { default = "ops@example.com" }
variable "image" {
  description = "Container image; the CD workflow overrides this with the built tag"
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}
variable "model_mode" {
  description = "'simulated' for the synthetic-data demo, 'azure' to call the Foundry-managed deployment"
  default     = "azure"
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "this" {
  name     = "rg-${var.app_name}"
  location = var.location
}

module "identity" {
  source              = "../../modules/identity"
  name                = var.app_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
}

module "entra_api" {
  source       = "../../modules/entra_api"
  display_name = "${var.app_name}-agent-api"
}

module "openai" {
  source              = "../../modules/openai"
  name                = var.app_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  user_principal_ids  = [module.identity.principal_id]
  deployments = {
    chat = { model_name = "gpt-4o", model_version = "2024-08-06", capacity = 30 }
  }
}

module "search" {
  source               = "../../modules/search"
  name                 = var.app_name
  location             = var.location
  resource_group_name  = azurerm_resource_group.this.name
  reader_principal_ids = [module.identity.principal_id]
}

module "keyvault" {
  source                       = "../../modules/keyvault"
  name                         = var.app_name
  location                     = var.location
  resource_group_name          = azurerm_resource_group.this.name
  tenant_id                    = data.azurerm_client_config.current.tenant_id
  secrets_reader_principal_ids = [module.identity.principal_id]
}

module "monitoring" {
  source              = "../../modules/monitoring"
  name                = var.app_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  alert_email         = var.alert_email
}

module "foundry" {
  source                  = "../../modules/foundry"
  name                    = var.app_name
  location                = var.location
  resource_group_name     = azurerm_resource_group.this.name
  key_vault_id            = module.keyvault.id
  application_insights_id = module.monitoring.app_insights_id
  openai_account_id       = module.openai.id
}

module "registry" {
  source              = "../../modules/registry"
  name                = var.app_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
}

module "containerapp" {
  source                     = "../../modules/containerapp"
  name                       = var.app_name
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  registry_id                = module.registry.id
  registry_login_server      = module.registry.login_server
  identity_id                = module.identity.id
  identity_principal_id      = module.identity.principal_id
  image                      = var.image
  env = {
    ENTRA_TENANT_ID                  = data.azurerm_client_config.current.tenant_id
    API_AUDIENCE                     = module.entra_api.audiences
    MODEL_MODE                       = var.model_mode
    ENTERPRISE_API_MODE              = "simulated" # synthetic demo; point at real systems later
    AZURE_OPENAI_ENDPOINT            = module.openai.endpoint
    AZURE_OPENAI_DEPLOYMENT          = "chat"
    AZURE_MANAGED_IDENTITY_CLIENT_ID = module.identity.client_id
  }
  secret_env = {
    APPLICATIONINSIGHTS_CONNECTION_STRING = module.monitoring.app_insights_connection_string
  }
}

output "api_url" { value = "https://${module.containerapp.fqdn}" }
output "api_client_id" { value = module.entra_api.client_id }
output "acr_login_server" { value = module.registry.login_server }
output "container_app_name" { value = module.containerapp.name }
output "foundry_project" { value = module.foundry.project_name }
output "resource_group" { value = azurerm_resource_group.this.name }
