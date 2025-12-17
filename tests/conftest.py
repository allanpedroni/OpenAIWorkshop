import os
import pytest
import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@pytest.fixture(scope="session")
def model_endpoint():
    return os.environ["MODEL_ENDPOINT"]


@pytest.fixture(scope="session")
def mcp_endpoint():
    return os.environ["MCP_ENDPOINT"]


@pytest.fixture(scope="session")
def backend_api_endpoint():
    return os.environ.get("BACKEND_API_ENDPOINT")


@pytest.fixture(scope="session")
def model_api_key():
    # If provided directly (e.g., GitHub secret), just use it
    key = os.environ.get("MODEL_API_KEY")
    if key:
        return key

    # Otherwise fetch from Key Vault using managed identity / OIDC
    kv_name = os.environ["KEYVAULT_NAME"]
    secret_name = os.environ["MODEL_API_KEY_SECRET_NAME"]

    vault_url = f"https://{kv_name}.vault.azure.net"
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    secret = client.get_secret(secret_name)

    return secret.value
