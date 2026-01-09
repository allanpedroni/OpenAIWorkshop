# User Assigned Managed Identity for Backend Container App
resource "azurerm_user_assigned_identity" "backend" {
  name                = "uami-be-${var.iteration}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

# Cognitive Services OpenAI User Role Assignment - Backend App
# Required for Entra ID / managed identity authentication to Azure OpenAI
# Allows inference API calls (chat completions, embeddings) without API keys
resource "azurerm_role_assignment" "openai_user_backend" {
  scope                = azurerm_ai_services.ai_hub.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.backend.principal_id
}

resource "azurerm_container_app" "backend" {
  name                         = "ca-be-${var.iteration}"
  container_app_environment_id = azurerm_container_app_environment.cae.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.backend.id]
  }

  ingress {
    target_port      = var.backend_target_port
    external_enabled = true
    transport        = "http"
    traffic_weight {
      percentage      = "100"
      latest_revision = true
    }

    cors {
      allow_credentials_enabled = true
      allowed_origins           = ["*"]
      allowed_headers           = ["*"]
      allowed_methods           = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }
  }

  # Registry configuration for ACR with managed identity
  registry {
    server   = local.acr_login_server
    identity = azurerm_user_assigned_identity.backend.id
  }

  # Cosmos DB key secret (only when not using managed identity)
  dynamic "secret" {
    for_each = var.use_cosmos_managed_identity ? [] : [1]
    content {
      name  = "cosmosdb-key"
      value = azurerm_cosmosdb_account.main.primary_key
    }
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "backend"
      # Use placeholder image for initial deployment if custom image not specified
      # After first deployment, update-containers.yml will set the real image
      # Using Microsoft's quickstart image as a known-good placeholder
      image  = var.docker_image_backend != "" ? var.docker_image_backend : "mcr.microsoft.com/k8se/quickstart:latest"
      cpu    = 1
      memory = "2Gi"

      readiness_probe {
        port      = var.backend_target_port
        transport = "HTTP"
        path      = "/docs"

        initial_delay           = 10
        interval_seconds        = 30
        failure_count_threshold = 3
      }

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        value = local.openai_endpoint
      }

      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = var.openai_api_version
      }

      env {
        name  = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value = var.openai_embedding_deployment_name
      }

      # ========== Cosmos DB Configuration ==========
      env {
        name  = "COSMOSDB_ENDPOINT"
        value = azurerm_cosmosdb_account.main.endpoint
      }

      env {
        name  = "COSMOS_DB_NAME"
        value = local.cosmos_database_name
      }

      env {
        name  = "COSMOS_CONTAINER_NAME"
        value = local.agent_state_container_name
      }

      # Cosmos DB key (only when not using managed identity)
      dynamic "env" {
        for_each = var.use_cosmos_managed_identity ? [] : [1]
        content {
          name        = "COSMOSDB_KEY"
          secret_name = "cosmosdb-key"
        }
      }

      # Managed Identity Client ID - always set for Azure OpenAI managed identity auth
      # Also used for Cosmos DB access when use_cosmos_managed_identity is true
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.backend.client_id
      }

      env {
        name  = "MANAGED_IDENTITY_CLIENT_ID"
        value = azurerm_user_assigned_identity.backend.client_id
      }

      # ========== AAD Authentication ==========
      env {
        name  = "AAD_TENANT_ID"
        value = var.aad_tenant_id
      }

      env {
        name  = "MCP_API_AUDIENCE"
        value = var.aad_api_audience
      }

      env {
        name  = "DISABLE_AUTH"
        value = tostring(var.disable_auth)
      }

      env {
        name  = "ALLOWED_EMAIL_DOMAIN"
        value = var.allowed_email_domain
      }

      # ========== MCP and Agent Configuration ==========
      env {
        name  = "MCP_SERVER_URI"
        # When MCP is internal-only, use internal FQDN; otherwise use public FQDN
        value = var.mcp_internal_only ? "http://${azurerm_container_app.mcp.name}.internal.${azurerm_container_app_environment.cae.default_domain}/mcp" : "https://${azurerm_container_app.mcp.ingress[0].fqdn}/mcp"
      }

      env {
        name  = "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
        value = var.openai_deployment_name
      }

      env {
        name  = "AZURE_OPENAI_CHAT_DEPLOYMENT"
        value = var.openai_deployment_name
      }

      env {
        name  = "OPENAI_MODEL_NAME"
        value = "${var.openai_model_name}-${var.openai_model_version}"
      }

      env {
        name  = "AGENT_MODULE"
        value = "agents.agent_framework.single_agent"
      }

      env {
        name  = "MAGENTIC_LOG_WORKFLOW_EVENTS"
        value = "true"
      }
      env {
        name  = "MAGENTIC_ENABLE_PLAN_REVIEW"
        value = "true"
      }
      env {
        name  = "MAGENTIC_MAX_ROUNDS"
        value = "10"
      }
      env {
        name  = "HANDOFF_CONTEXT_TRANSFER_TURNS"
        value = "-1"
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
    azurerm_role_assignment.openai_user_backend,
    azurerm_role_assignment.acr_pull_backend,
    azurerm_cosmosdb_sql_role_assignment.backend_data_owner,
    azurerm_cosmosdb_sql_role_assignment.backend_data_contributor
  ]
}
