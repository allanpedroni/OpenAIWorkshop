resource "azurerm_log_analytics_workspace" "laws" {
  name                = "log-${local.web_app_name_prefix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = local.common_tags
}

resource "azurerm_container_app_environment" "cae" {
  name                       = "cae-${local.web_app_name_prefix}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.laws.id
  infrastructure_subnet_id   = var.enable_networking ? azurerm_subnet.container_apps[0].id : null

  tags = local.common_tags
}