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
  key_vault_name       = "kv-${substr(local.name_prefix, 0, 14)}-${substr(var.iteration, -2, -1)}"
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
  public_network_access              = "Enabled"
  resource_group_name                = azurerm_resource_group.rg.name
  sku_name                           = "S0"
  tags                               = local.common_tags

  identity {
    identity_ids = []
    type         = "SystemAssigned"
  }

  network_acls {
    default_action = "Allow"
    ip_rules       = []
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_key_vault" "main" {
  name                       = local.key_vault_name
  location                   = var.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  # Enable RBAC authorization (recommended over access policies)
  rbac_authorization_enabled = true

  # Network settings
  public_network_access_enabled = true

  network_acls {
    bypass         = "AzureServices"
    default_action = "Allow"
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# Key Vault Role Assignment - Current User (Key Vault Administrator)
resource "azurerm_role_assignment" "kv_admin_current_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}
