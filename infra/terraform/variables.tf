variable "project_name" { 
  type    = string 
  default = "OpenAIWorkshop"
}
variable "location" {
  type    = string
  default = "eastus2"
}
variable "tenant_id" { type = string }
variable "subscription_id" { type = string }
variable "acr_name" { 
  description = "Name of existing ACR (only used when create_acr = false)"
  type    = string 
  default = ""
}

variable "create_openai_deployment" {
  description = "Create OpenAI model deployment. Set to false to use existing deployment."
  type        = bool
  default     = true
}

variable "openai_deployment_name" {
  description = "Name of the OpenAI model deployment"
  type        = string
  default     = "gpt-4.1"
}

variable "openai_model_name" {
  description = "OpenAI model name to deploy"
  type        = string
  default     = "gpt-4.1"
}

variable "openai_model_version" {
  description = "OpenAI model version"
  type        = string
  default     = "2025-04-14"
}

variable "openai_deployment_capacity" {
  description = "Capacity (TPM in thousands) for OpenAI deployment"
  type        = number
  default     = 10
}

variable "iteration" {
  description = "An iteration counter for things to prevent soft deletion issues."
  type        = string
  default     = "001"
}


variable "docker_image_backend" {
  description = "Docker image name (e.g., 'nginx:latest', 'httpd:alpine'). Leave empty to use runtime stack instead."
  type        = string
  default     = ""
}

variable "docker_image_mcp" {
  description = "Docker image name (e.g., 'nginx:latest', 'httpd:alpine'). Leave empty to use runtime stack instead."
  type        = string
  default     = ""
}

variable "docker_registry_url" {
  description = "Docker registry URL (e.g., 'https://index.docker.io' for Docker Hub). Only needed for private registries."
  type        = string
  default     = ""
}

variable "docker_registry_username" {
  description = "Username for private Docker registry authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "docker_registry_password" {
  description = "Password for private Docker registry authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "environment" {
  description = "Deployment environment (e.g., dev, integration, prod)"
  type        = string
  default     = "dev"
}

# ============================================================================
# Cosmos DB Variables
# ============================================================================

variable "use_cosmos_managed_identity" {
  description = "Enable managed identity for Cosmos DB access (recommended). When false, uses connection keys."
  type        = bool
  default     = true
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint for Cosmos DB (disables public network access)"
  type        = bool
  default     = false
}

# ============================================================================
# Networking Variables
# ============================================================================

variable "enable_networking" {
  description = "Enable VNet integration for Container Apps and private endpoints"
  type        = bool
  default     = false
}

variable "vnet_address_prefix" {
  description = "Address space for the virtual network"
  type        = string
  default     = "10.10.0.0/16"
}

variable "container_apps_subnet_prefix" {
  description = "Subnet CIDR for the Container Apps managed environment infrastructure (must be at least /23)"
  type        = string
  default     = "10.10.0.0/23"
}

variable "private_endpoint_subnet_prefix" {
  description = "Subnet CIDR for private endpoints (Cosmos DB, etc.)"
  type        = string
  default     = "10.10.2.0/24"
}

# ============================================================================
# Container Registry Variables
# ============================================================================

variable "create_acr" {
  description = "Create a new Azure Container Registry. Set to false to use an existing one."
  type        = bool
  default     = true
}

variable "acr_sku" {
  description = "SKU for the Azure Container Registry"
  type        = string
  default     = "Basic"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.acr_sku)
    error_message = "ACR SKU must be Basic, Standard, or Premium."
  }
}

variable "acr_resource_group" {
  description = "Resource group of existing ACR (only used when create_acr = false)"
  type        = string
  default     = ""
}

# ============================================================================
# AAD Authentication Variables
# ============================================================================

variable "aad_tenant_id" {
  description = "AAD tenant ID for authentication. Empty to use current tenant context."
  type        = string
  default     = ""
}

variable "aad_client_id" {
  description = "Public client ID (frontend app registration) for token requests."
  type        = string
  default     = ""
}

variable "aad_api_audience" {
  description = "App ID URI (audience) for the protected API."
  type        = string
  default     = ""
}

variable "disable_auth" {
  description = "Disable authentication in the backend (for development only)"
  type        = bool
  default     = true
}

variable "allowed_email_domain" {
  description = "Allowed email domain for authenticated users when auth is enabled"
  type        = string
  default     = "microsoft.com"
}

# ============================================================================
# Tags Variable
# ============================================================================

variable "tags" {
  description = "Tags to apply to all resources. Will be merged with default tags."
  type        = map(string)
  default     = {}
}

# ============================================================================
# OpenAI Embedding Deployment
# ============================================================================

variable "create_openai_embedding_deployment" {
  description = "Create OpenAI embedding model deployment. Set to false to use existing deployment."
  type        = bool
  default     = true
}

variable "openai_embedding_deployment_name" {
  description = "Name of the OpenAI embedding model deployment"
  type        = string
  default     = "text-embedding-ada-002"
}

variable "openai_embedding_model_name" {
  description = "OpenAI embedding model name"
  type        = string
  default     = "text-embedding-ada-002"
}

variable "openai_embedding_model_version" {
  description = "OpenAI embedding model version"
  type        = string
  default     = "2"
}

# ============================================================================
# Container App Configuration
# ============================================================================

variable "backend_target_port" {
  description = "Target port for the backend container app"
  type        = number
  default     = 3000
}

variable "mcp_target_port" {
  description = "Target port for the MCP container app"
  type        = number
  default     = 8000
}

variable "container_image_tag" {
  description = "Default container image tag"
  type        = string
  default     = "latest"
}