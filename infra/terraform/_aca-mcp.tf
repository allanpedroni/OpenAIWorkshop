# User Assigned Managed Identity for MCP Container App
resource "azurerm_user_assigned_identity" "mcp" {
  name                = "uami-mcp-${var.iteration}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

resource "azurerm_container_app" "mcp" {
  name                         = "ca-mcp-${var.iteration}"
  container_app_environment_id = azurerm_container_app_environment.cae.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.mcp.id]
  }

  ingress {
    target_port      = var.mcp_target_port
    external_enabled = var.mcp_internal_only ? false : true
    transport        = "http"
    # Allow HTTP (non-TLS) connections for internal communication
    # This is safe because the MCP service is internal-only (not exposed to internet)
    allow_insecure_connections = var.mcp_internal_only ? true : false
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # Registry configuration for ACR with managed identity
  registry {
    server   = local.acr_login_server
    identity = azurerm_user_assigned_identity.mcp.id
  }

  # Cosmos DB key secret (only when not using managed identity)
  dynamic "secret" {
    for_each = var.use_cosmos_managed_identity ? [] : [1]
    content {
      name                = "cosmosdb-key"
      identity            = azurerm_user_assigned_identity.mcp.id
      key_vault_secret_id = azurerm_key_vault_secret.cosmos_primary_key[0].versionless_id
    }
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "mcp"
      # Use placeholder image for initial deployment if custom image not specified
      # After first deployment, update-containers.yml will set the real image
      # Using Microsoft's quickstart image as a known-good placeholder
      image  = var.docker_image_mcp != "" ? var.docker_image_mcp : "mcr.microsoft.com/k8se/quickstart:latest"
      cpu    = 0.5
      memory = "1Gi"

      # ========== Cosmos DB Configuration ==========
      # Enable Cosmos DB backend for MCP service
      env {
        name  = "USE_COSMOSDB"
        value = "true"
      }

      env {
        name  = "COSMOSDB_ENDPOINT"
        value = azurerm_cosmosdb_account.main.endpoint
      }

      env {
        name  = "COSMOS_DATABASE_NAME"
        value = local.cosmos_database_name
      }

      env {
        name  = "COSMOS_CONTAINER_NAME"
        value = local.agent_state_container_name
      }

      env {
        name  = "COSMOS_USE_MANAGED_IDENTITY"
        value = tostring(var.use_cosmos_managed_identity)
      }

      # Cosmos DB key (only when not using managed identity)
      dynamic "env" {
        for_each = var.use_cosmos_managed_identity ? [] : [1]
        content {
          name        = "COSMOSDB_KEY"
          secret_name = "cosmosdb-key"
        }
      }

      # Managed Identity Client ID (for Cosmos DB access)
      dynamic "env" {
        for_each = var.use_cosmos_managed_identity ? [1] : []
        content {
          name  = "AZURE_CLIENT_ID"
          value = azurerm_user_assigned_identity.mcp.client_id
        }
      }

      dynamic "env" {
        for_each = var.use_cosmos_managed_identity ? [1] : []
        content {
          name  = "MANAGED_IDENTITY_CLIENT_ID"
          value = azurerm_user_assigned_identity.mcp.client_id
        }
      }

      # ========== Authentication ==========
      env {
        name  = "DISABLE_AUTH"
        value = tostring(var.disable_auth)
      }
    }

  }

  lifecycle {
    # Ignore image changes - managed by update-containers.yml workflow
    # This prevents Terraform from reverting to placeholder after update-containers sets real image
    ignore_changes = [
      template[0].container[0].image
    ]
  }

  depends_on = [
    azurerm_role_assignment.acr_pull_mcp,
    azurerm_cosmosdb_sql_role_assignment.mcp_data_owner,
    azurerm_cosmosdb_sql_role_assignment.mcp_data_contributor
  ]
}
