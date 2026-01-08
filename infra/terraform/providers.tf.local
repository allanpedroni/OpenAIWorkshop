terraform {
  required_version = ">= 1.12.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.49.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = ">= 3.6.0"
    }
        random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
  }
}


provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }

    application_insights {
      disable_generated_rule = false
    }

    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
}


provider "azuread" {
  tenant_id = var.tenant_id
}

provider "random" {
  # Configuration options
}