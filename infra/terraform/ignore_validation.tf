resource "azurerm_cognitive_deployment" "gpt" {
  count                = var.create_openai_deployment ? 1 : 0
  cognitive_account_id = azurerm_ai_services.ai_hub.id
  name                 = var.openai_deployment_name

  model {
    format  = "OpenAI"
    name    = var.openai_model_name
    version = var.openai_model_version
  }

  sku {
    capacity = var.openai_deployment_capacity
    name     = "GlobalStandard"
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  count                = var.create_openai_embedding_deployment ? 1 : 0
  cognitive_account_id = azurerm_ai_services.ai_hub.id
  name                 = var.openai_embedding_deployment_name

  model {
    format  = "OpenAI"
    name    = var.openai_embedding_model_name
    version = var.openai_embedding_model_version
  }

  sku {
    capacity = 10
    name     = "Standard"
  }

  depends_on = [azurerm_cognitive_deployment.gpt]
}