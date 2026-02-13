# Production environment configuration
environment      = "production"
location         = "eastus2"
project_name     = "OpenAIWorkshop"
iteration        = "002"
tenant_id        = "0fbe7234-45ea-498b-b7e4-1a8b2d3be4d9"
subscription_id  = "840b5c5c-3f4a-459a-94fc-6bad2a969f9d"

# Optional: Set to false if you want to use API keys (not recommended)
use_cosmos_managed_identity = true

# OpenAI deployment configuration
create_openai_deployment = true
openai_deployment_name   = "gpt-5.2-chat"
openai_model_name        = "gpt-5.2-chat"
openai_model_version     = "2025-12-11"
openai_api_version       = "2025-04-01-preview"
openai_deployment_capacity = 200  # 200k tokens/minute

# OpenAI embedding deployment configuration
create_openai_embedding_deployment = true
openai_embedding_deployment_name   = "text-embedding-ada-002"
openai_embedding_model_name        = "text-embedding-ada-002"
openai_embedding_model_version     = "2"

# Networking configuration
enable_networking       = true
enable_private_endpoint = true
vnet_address_prefix            = "10.10.0.0/16"
container_apps_subnet_prefix   = "10.10.0.0/23"
private_endpoint_subnet_prefix = "10.10.2.0/24"

# MCP Service Security
mcp_internal_only = true
