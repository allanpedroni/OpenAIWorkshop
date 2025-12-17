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
  value       = azurerm_cognitive_deployment.gpt.name
}

output "openai_endpoint" {
  description = "Endpoint URL for the Azure OpenAI service"
  value       = local.model_endpoint
}

output "openai_deployment_name" {
  description = "Name of the OpenAI model deployment"
  value       = azurerm_cognitive_deployment.gpt.name
}

# Key Vault
output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = azurerm_key_vault.main.id
}

output "mcp_aca_url" {
  description = "URL of the mcp container app"
  value       = "https://${azurerm_container_app.mcp.ingress[0].fqdn}"
}

output "be_aca_url" {
  description = "URL of the backend container app"
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}