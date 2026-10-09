variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "reader_principal_ids" {
  type    = list(string)
  default = []
}
variable "tags" {
  type    = map(string)
  default = {}
}

resource "azurerm_search_service" "this" {
  name                         = "${var.name}-search"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  sku                          = "basic"
  local_authentication_enabled = false # Entra ID only
  tags                         = var.tags
}

resource "azurerm_role_assignment" "reader" {
  for_each             = toset(var.reader_principal_ids)
  scope                = azurerm_search_service.this.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = each.value
}

output "endpoint" { value = "https://${azurerm_search_service.this.name}.search.windows.net" }
output "id" { value = azurerm_search_service.this.id }
