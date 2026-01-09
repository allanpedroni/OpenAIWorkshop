"""Contoso Customer Service Utility Module

Unified module that provides async functions for interacting with the Contoso
customer database. Supports both SQLite (local development) and Cosmos DB
(production) backends, selectable via environment variable.

Usage:
    Set USE_COSMOSDB=true to use Cosmos DB backend
    Set USE_COSMOSDB=false (default) to use SQLite backend

All functions are exported with the same interface regardless of backend.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend selection
USE_COSMOSDB = os.getenv("USE_COSMOSDB", "false").lower() in ("true", "1", "yes", "on")

if USE_COSMOSDB:
    # Import all functions from Cosmos DB backend
    from _backend_cosmos import (
        get_all_customers_async,
        get_customer_detail_async,
        get_customer_orders_async,
        get_subscription_detail_async,
        update_subscription_async,
        get_data_usage_async,
        get_billing_summary_async,
        get_invoice_payments_async,
        pay_invoice_async,
        get_security_logs_async,
        unlock_account_async,
        get_products_async,
        get_product_detail_async,
        get_promotions_async,
        get_eligible_promotions_async,
        get_support_tickets_async,
        create_support_ticket_async,
        search_knowledge_base_async,
        get_embedding,
    )
    _BACKEND = "cosmosdb"
else:
    # Import all functions from SQLite backend
    from _backend_sqlite import (
        get_all_customers_async,
        get_customer_detail_async,
        get_customer_orders_async,
        get_subscription_detail_async,
        update_subscription_async,
        get_data_usage_async,
        get_billing_summary_async,
        get_invoice_payments_async,
        pay_invoice_async,
        get_security_logs_async,
        unlock_account_async,
        get_products_async,
        get_product_detail_async,
        get_promotions_async,
        get_eligible_promotions_async,
        get_support_tickets_async,
        create_support_ticket_async,
        search_knowledge_base_async,
        get_embedding,
    )
    _BACKEND = "sqlite"


def get_backend_name() -> str:
    """Return the name of the active backend."""
    return _BACKEND


# Export all functions
__all__ = [
    # Backend info
    "get_backend_name",
    # Customer functions
    "get_all_customers_async",
    "get_customer_detail_async",
    "get_customer_orders_async",
    # Subscription functions
    "get_subscription_detail_async",
    "update_subscription_async",
    "get_data_usage_async",
    # Billing functions
    "get_billing_summary_async",
    "get_invoice_payments_async",
    "pay_invoice_async",
    # Security functions
    "get_security_logs_async",
    "unlock_account_async",
    # Product functions
    "get_products_async",
    "get_product_detail_async",
    # Promotion functions
    "get_promotions_async",
    "get_eligible_promotions_async",
    # Support functions
    "get_support_tickets_async",
    "create_support_ticket_async",
    # Knowledge base functions
    "search_knowledge_base_async",
    # Embedding function
    "get_embedding",
]
