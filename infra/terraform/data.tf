# Data Sources
# Query existing Azure resources and configuration

# Current Azure client configuration
data "azurerm_client_config" "current" {}

# Current Azure subscription
# tflint-ignore: terraform_unused_declarations
data "azurerm_subscription" "current" {}