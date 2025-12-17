resource "azurerm_cognitive_deployment" "gpt" {
  cognitive_account_id = azurerm_ai_services.ai_hub.id
  name                 = var.openai_deployment_name

  model {
    format  = "OpenAI"
    name    = var.openai_model_name
    version = var.openai_model_version
  }

  sku {
    capacity = 50
    name     = "GlobalStandard"
  }
}