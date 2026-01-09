# Cosmos DB Account, Database, and Containers
# Aligned with Bicep modules/cosmosdb.bicep

locals {
  cosmos_db_name            = lower("${var.project_name}-${local.env}-cosmos-${var.iteration}")
  cosmos_database_name      = "contoso"
  agent_state_container_name = "workshop_agent_state_store"
}

resource "azurerm_cosmosdb_account" "main" {
  name                = local.cosmos_db_name
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
    zone_redundant    = false
  }

  capabilities {
    name = "EnableNoSQLVectorSearch"
  }

  # Disable local auth when using managed identity exclusively
  local_authentication_disabled = false
  public_network_access_enabled = var.enable_private_endpoint ? false : true

  tags = local.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# SQL Database
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = local.cosmos_database_name
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
}

# Customers container
resource "azurerm_cosmosdb_sql_container" "customers" {
  name                = "Customers"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/customer_id"]

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

# Subscriptions container
resource "azurerm_cosmosdb_sql_container" "subscriptions" {
  name                = "Subscriptions"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/customer_id"]
}

# Products container
resource "azurerm_cosmosdb_sql_container" "products" {
  name                = "Products"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/category"]
}

# Promotions container
resource "azurerm_cosmosdb_sql_container" "promotions" {
  name                = "Promotions"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/id"]
}

# Agent State Store container (hierarchical partition key)
resource "azurerm_cosmosdb_sql_container" "agent_state" {
  name                = local.agent_state_container_name
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/tenant_id", "/id"]
  partition_key_kind  = "MultiHash"
  partition_key_version = 2
}


