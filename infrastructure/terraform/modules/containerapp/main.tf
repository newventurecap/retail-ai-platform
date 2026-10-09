variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "registry_id" { type = string }
variable "registry_login_server" { type = string }
variable "identity_id" { type = string }
variable "identity_principal_id" { type = string }
variable "image" { type = string }
variable "env" {
  description = "Plain environment variables"
  type        = map(string)
  default     = {}
}
variable "secret_env" {
  description = "Environment variables sourced from container app secrets"
  type        = map(string)
  default     = {}
  sensitive   = true
}
variable "min_replicas" {
  type    = number
  default = 1
}
variable "max_replicas" {
  type    = number
  default = 3
}
variable "tags" {
  type    = map(string)
  default = {}
}

resource "azurerm_container_app_environment" "this" {
  name                       = "${var.name}-cae"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.registry_id
  role_definition_name = "AcrPull"
  principal_id         = var.identity_principal_id
}

resource "azurerm_container_app" "this" {
  name                         = "${var.name}-api"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  registry {
    server   = var.registry_login_server
    identity = var.identity_id
  }

  dynamic "secret" {
    for_each = nonsensitive(keys(var.secret_env))
    content {
      name  = lower(replace(secret.value, "_", "-"))
      value = var.secret_env[secret.value]
    }
  }

  ingress {
    external_enabled = true # reachable by Copilot Studio; every call still needs an Entra token
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "api"
      image  = var.image
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = nonsensitive(keys(var.secret_env))
        content {
          name        = env.value
          secret_name = lower(replace(env.value, "_", "-"))
        }
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/healthz"
        port      = 8000
      }
      readiness_probe {
        transport = "HTTP"
        path      = "/healthz"
        port      = 8000
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image] # CD rolls out images via `az containerapp update`
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}

output "fqdn" { value = azurerm_container_app.this.ingress[0].fqdn }
output "name" { value = azurerm_container_app.this.name }
