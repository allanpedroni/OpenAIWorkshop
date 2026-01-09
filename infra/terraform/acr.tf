# Azure Container Registry
# Aligned with Bicep modules/container-registry.bicep

locals {
  # ACR name must be alphanumeric only
  acr_name_generated = replace("${var.project_name}${local.env}acr${var.iteration}", "-", "")
}

resource "azurerm_container_registry" "main" {
  count               = var.create_acr ? 1 : 0
  name                = local.acr_name_generated
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
  sku                 = var.acr_sku
  admin_enabled       = true

  public_network_access_enabled = true
  network_rule_bypass_option    = "AzureServices"

  tags = local.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# Data source for existing ACR (when not creating)
data "azurerm_container_registry" "existing" {
  count               = var.create_acr ? 0 : 1
  name                = var.acr_name
  resource_group_name = var.acr_resource_group != "" ? var.acr_resource_group : azurerm_resource_group.rg.name
}

locals {
  # Use created ACR or existing ACR
  acr_login_server = var.create_acr ? azurerm_container_registry.main[0].login_server : data.azurerm_container_registry.existing[0].login_server
  acr_name_final   = var.create_acr ? azurerm_container_registry.main[0].name : data.azurerm_container_registry.existing[0].name
  acr_admin_username = var.create_acr ? azurerm_container_registry.main[0].admin_username : data.azurerm_container_registry.existing[0].admin_username
  acr_admin_password = var.create_acr ? azurerm_container_registry.main[0].admin_password : null
}

# Grant Backend identity AcrPull role
resource "azurerm_role_assignment" "acr_pull_backend" {
  count                = var.create_acr ? 1 : 0
  scope                = azurerm_container_registry.main[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.backend.principal_id
}

# Grant MCP identity AcrPull role
resource "azurerm_role_assignment" "acr_pull_mcp" {
  count                = var.create_acr ? 1 : 0
  scope                = azurerm_container_registry.main[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.mcp.principal_id
}
