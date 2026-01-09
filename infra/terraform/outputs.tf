# Resource Group
output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.rg.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.rg.location
}

output "resource_group_id" {
  description = "ID of the created resource group"
  value       = azurerm_resource_group.rg.id
}

# Azure AI Hub
output "ai_hub_name" {
  description = "Name of the Azure AI Hub (Machine Learning Workspace)"
  value       = azurerm_ai_services.ai_hub.name
}

output "ai_hub_id" {
  description = "ID of the Azure AI Hub"
  value       = azurerm_ai_services.ai_hub.id
}

# Azure OpenAI
output "openai_account_name" {
  description = "Name of the Azure OpenAI account"
  value       = var.create_openai_deployment ? azurerm_cognitive_deployment.gpt[0].name : var.openai_deployment_name
}

output "openai_endpoint" {
  description = "Endpoint URL for the Azure OpenAI service"
  value       = local.model_endpoint
}

output "openai_deployment_name" {
  description = "Name of the OpenAI model deployment"
  value       = var.create_openai_deployment ? azurerm_cognitive_deployment.gpt[0].name : var.openai_deployment_name
}

output "mcp_aca_url" {
  description = "URL of the mcp container app"
  value       = "https://${azurerm_container_app.mcp.ingress[0].fqdn}"
}

output "be_aca_url" {
  description = "URL of the backend container app"
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

# ============================================================================
# Cosmos DB Outputs (aligned with Bicep)
# ============================================================================

output "cosmosdb_endpoint" {
  description = "Cosmos DB endpoint URL"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmosdb_account_name" {
  description = "Cosmos DB account name"
  value       = azurerm_cosmosdb_account.main.name
}

output "cosmosdb_database_name" {
  description = "Cosmos DB database name"
  value       = local.cosmos_database_name
}

output "cosmosdb_agent_state_container" {
  description = "Cosmos DB agent state container name"
  value       = local.agent_state_container_name
}

# ============================================================================
# Container Registry Outputs (aligned with Bicep)
# ============================================================================

output "container_registry_name" {
  description = "Name of the Container Registry"
  value       = local.acr_name_final
}

output "container_registry_login_server" {
  description = "Login server for the Container Registry"
  value       = local.acr_login_server
}

output "container_registry_id" {
  description = "ID of the Container Registry"
  value       = var.create_acr ? azurerm_container_registry.main[0].id : data.azurerm_container_registry.existing[0].id
}

# ============================================================================
# Container Apps Environment
# ============================================================================

output "container_apps_environment_id" {
  description = "ID of the Container Apps Environment"
  value       = azurerm_container_app_environment.cae.id
}

output "container_apps_environment_name" {
  description = "Name of the Container Apps Environment"
  value       = azurerm_container_app_environment.cae.name
}

# ============================================================================
# Managed Identities
# ============================================================================

output "backend_identity_client_id" {
  description = "Client ID of the backend managed identity"
  value       = azurerm_user_assigned_identity.backend.client_id
}

output "mcp_identity_client_id" {
  description = "Client ID of the MCP managed identity"
  value       = azurerm_user_assigned_identity.mcp.client_id
}