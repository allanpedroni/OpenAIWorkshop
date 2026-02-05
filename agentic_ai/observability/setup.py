# Copyright (c) Microsoft. All rights reserved.

"""
Observability setup for Agent Framework applications with Application Insights.

This module configures OpenTelemetry to send traces, logs, and metrics to 
Azure Application Insights, enabling full observability of agent executions.

Azure Monitor Dashboards (no Grafana required):
    - Agent Overview: https://aka.ms/amg/dash/af-agent
    - Workflow Overview: https://aka.ms/amg/dash/af-workflow

Usage:
    1. Set APPLICATIONINSIGHTS_CONNECTION_STRING in your .env
    2. Call setup_observability() once at app startup
    3. All Agent Framework traces are captured automatically
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Track initialization state
_initialized = False


def setup_observability(
    connection_string: Optional[str] = None,
    service_name: str = "contoso-agent",
    enable_live_metrics: bool = True,
    enable_sensitive_data: bool = False,
) -> bool:
    """
    Configure Application Insights for Agent Framework observability.
    
    This follows the pattern from agent-framework/python/samples/getting_started/observability/.
    
    Args:
        connection_string: App Insights connection string (or set APPLICATIONINSIGHTS_CONNECTION_STRING).
        service_name: Service name shown in App Insights.
        enable_live_metrics: Enable Live Metrics stream.
        enable_sensitive_data: Include prompts/responses in traces (dev only!).
    
    Returns:
        True if setup succeeded, False otherwise.
    """
    global _initialized
    
    if _initialized:
        return True
    
    # Get connection string from parameter or environment
    conn_str = connection_string or os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if not conn_str:
        logger.debug("No APPLICATIONINSIGHTS_CONNECTION_STRING - observability disabled")
        return False
    
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from agent_framework.observability import create_resource, enable_instrumentation
        
        # Set service name via standard env var
        os.environ.setdefault("OTEL_SERVICE_NAME", service_name)
        
        # Configure Azure Monitor (same pattern as agent-framework samples)
        configure_azure_monitor(
            connection_string=conn_str,
            resource=create_resource(),
            enable_live_metrics=enable_live_metrics,
        )
        
        # Enable Agent Framework instrumentation
        enable_instrumentation(enable_sensitive_data=enable_sensitive_data)
        
        _initialized = True
        print(f"✅ Application Insights observability enabled (service: {service_name})")
        logger.info(f"✅ Application Insights observability enabled (service: {service_name})")
        return True
        
    except ImportError as e:
        print(f"❌ Observability dependencies not installed: {e}")
        logger.warning(f"Observability dependencies not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to configure observability: {e}")
        logger.warning(f"Failed to configure observability: {e}")
        return False


def get_tracer(name: str = "contoso-agent"):
    """Get an OpenTelemetry tracer for creating custom spans."""
    from agent_framework.observability import get_tracer as af_get_tracer
    return af_get_tracer(name)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID for correlation."""
    from opentelemetry import trace
    from opentelemetry.trace.span import format_trace_id
    
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        return format_trace_id(current_span.get_span_context().trace_id)
    return None
