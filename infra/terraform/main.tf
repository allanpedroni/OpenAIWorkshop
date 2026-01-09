locals {
  env      = var.environment
  name_prefix = "${var.project_name}-${local.env}"

  rg_name  = "rg-${local.name_prefix}-${var.iteration}"
  asp_name = "asp-${var.project_name}-${local.env}"
  app_name = "app-${var.project_name}-${local.env}"
  ai_hub_name = "aih-${var.project_name}-${local.env}-${var.iteration}"
  ai_hub_subdomain = lower(local.ai_hub_name)  # Custom subdomain must be lowercase
  model_endpoint = "https://${local.ai_hub_subdomain}.openai.azure.com/openai/v1/chat/completions"
  openai_endpoint = "https://${local.ai_hub_subdomain}.openai.azure.com"
  web_app_name_prefix  = "${local.name_prefix}-${var.iteration}"

  # Merge user-provided tags with default tags
  default_tags = {
    env         = local.env
    project     = var.project_name
    ManagedBy   = "Terraform"
    Application = "OpenAI-Workshop"
  }
  common_tags = merge(local.default_tags, var.tags)
}


resource "azurerm_resource_group" "rg" {
  name     = local.rg_name
  location = var.location
  tags     = { env = local.env, project = var.project_name  }
}


resource "azurerm_ai_services" "ai_hub" {
  custom_subdomain_name              = local.ai_hub_subdomain
  fqdns                              = []
  local_authentication_enabled       = true
  location                           = "East US 2"
  name                               = local.ai_hub_name
  outbound_network_access_restricted = false
  public_network_access              = var.enable_private_endpoint ? "Disabled" : "Enabled"
  resource_group_name                = azurerm_resource_group.rg.name
  sku_name                           = "S0"
  tags                               = local.common_tags

  identity {
    identity_ids = []
    type         = "SystemAssigned"
  }

  network_acls {
    default_action = var.enable_private_endpoint ? "Deny" : "Allow"
    ip_rules       = []
  }

  lifecycle {
    ignore_changes = [tags]
  }
}


