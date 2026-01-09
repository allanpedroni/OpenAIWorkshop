import os  
import logging  
from typing import Any, Dict, List, Optional, Union  
from dotenv import load_dotenv  

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.core.credentials import TokenCredential

load_dotenv()  # Load environment variables from .env file if needed  
  
class BaseAgent:  
    """  
    Base class for all agents.  
    Not intended to be used directly.  
    Handles environment variables, state store, and chat history.
    
    Supports both API key and managed identity authentication for Azure OpenAI.
    When AZURE_OPENAI_API_KEY is not set, uses DefaultAzureCredential (or 
    ManagedIdentityCredential if AZURE_CLIENT_ID is set for user-assigned identity).
    """  
  
    def __init__(self, state_store: Dict[str, Any], session_id: str) -> None:  
        self.azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
        self.azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")  
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")  
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")  
        self.mcp_server_uri = os.getenv("MCP_SERVER_URI") 
        self.openai_model_name = os.getenv("OPENAI_MODEL_NAME")
        
        # Initialize credential for managed identity authentication
        self.azure_credential: Optional[TokenCredential] = None
        if not self.azure_openai_key:
            azure_client_id = os.getenv("AZURE_CLIENT_ID")
            if azure_client_id:
                # Use user-assigned managed identity
                self.azure_credential = ManagedIdentityCredential(client_id=azure_client_id)
                logging.info(f"Using ManagedIdentityCredential with client_id: {azure_client_id}")
            else:
                # Use DefaultAzureCredential (works with system-assigned MI, Azure CLI, etc.)
                self.azure_credential = DefaultAzureCredential()
                logging.info("Using DefaultAzureCredential for Azure OpenAI authentication")  
  
        self.session_id = session_id  
        self.state_store = state_store  
  
        self.chat_history: List[Dict[str, str]] = self.state_store.get(f"{session_id}_chat_history", [])  
        self.state: Optional[Any] = self.state_store.get(session_id, None) 
        logging.debug(f"Chat history for session {session_id}: {self.chat_history}")  
  
    def _setstate(self, state: Any) -> None:  
        self.state_store[self.session_id] = state  
  
    def append_to_chat_history(self, messages: List[Dict[str, str]]) -> None:  
        self.chat_history.extend(messages)  
        self.state_store[f"{self.session_id}_chat_history"] = self.chat_history  
  
    def set_websocket_manager(self, manager: Any) -> None:
        """
        Allow backend to inject WebSocket manager for streaming events.
        Override in child class if streaming support is needed.
        """
        pass  # Default: no-op for agents that don't support streaming
  
    async def chat_async(self, prompt: str) -> str:  
        """  
        Override in child class!  
        """  
        raise NotImplementedError("chat_async should be implemented in subclass.")  