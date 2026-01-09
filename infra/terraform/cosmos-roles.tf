# Cosmos DB RBAC Role Assignments
# Aligned with Bicep modules/cosmos-roles.bicep

# Built-in Cosmos DB SQL role definition IDs
# Data Owner: 00000000-0000-0000-0000-000000000001
# Data Contributor: 00000000-0000-0000-0000-000000000002

# Cosmos DB Data Owner role for Backend identity
resource "azurerm_cosmosdb_sql_role_assignment" "backend_data_owner" {
  count               = var.use_cosmos_managed_identity ? 1 : 0
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "${azurerm_cosmosdb_account.main.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001"
  principal_id        = azurerm_user_assigned_identity.backend.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Cosmos DB Data Contributor role for Backend identity
resource "azurerm_cosmosdb_sql_role_assignment" "backend_data_contributor" {
  count               = var.use_cosmos_managed_identity ? 1 : 0
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "${azurerm_cosmosdb_account.main.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_user_assigned_identity.backend.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Cosmos DB Data Owner role for MCP identity
resource "azurerm_cosmosdb_sql_role_assignment" "mcp_data_owner" {
  count               = var.use_cosmos_managed_identity ? 1 : 0
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "${azurerm_cosmosdb_account.main.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001"
  principal_id        = azurerm_user_assigned_identity.mcp.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Cosmos DB Data Contributor role for MCP identity
resource "azurerm_cosmosdb_sql_role_assignment" "mcp_data_contributor" {
  count               = var.use_cosmos_managed_identity ? 1 : 0
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "${azurerm_cosmosdb_account.main.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_user_assigned_identity.mcp.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}
