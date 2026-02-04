"""
Durable Task Client for Fraud Detection Testing.

This client demonstrates:
1. Starting a fraud detection orchestration
2. Monitoring orchestration status
3. Sending analyst decisions (external events)
4. Viewing results

Prerequisites:
- Worker must be running (python worker.py)
- DTS emulator running on port 8080
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from durabletask.azuremanaged.client import DurableTaskSchedulerClient
from durabletask.client import OrchestrationState

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
ANALYST_APPROVAL_EVENT = "AnalystDecision"
ORCHESTRATION_NAME = "fraud_detection_orchestration"


# ============================================================================
# Sample Alerts
# ============================================================================

SAMPLE_ALERTS = {
    "ALERT-001": {
        "alert_id": "ALERT-001",
        "customer_id": 1,
        "alert_type": "multi_country_login",
        "description": "Login attempts from USA and Russia within 2 hours",
        "timestamp": datetime.now().isoformat(),
        "severity": "high",
        "approval_timeout_hours": 0.05,  # 3 minutes for demo
    },
    "ALERT-002": {
        "alert_id": "ALERT-002",
        "customer_id": 2,
        "alert_type": "data_spike",
        "description": "Data usage increased by 500% in last 24 hours",
        "timestamp": datetime.now().isoformat(),
        "severity": "medium",
        "approval_timeout_hours": 0.05,
    },
    "ALERT-003": {
        "alert_id": "ALERT-003",
        "customer_id": 3,
        "alert_type": "unusual_charges",
        "description": "Three large purchases totaling $5,000 in 10 minutes",
        "timestamp": datetime.now().isoformat(),
        "severity": "high",
        "approval_timeout_hours": 0.05,
    },
}


# ============================================================================
# Client Helpers
# ============================================================================


def get_client() -> DurableTaskSchedulerClient:
    """Create a configured DurableTaskSchedulerClient."""
    taskhub_name = os.getenv("DTS_TASKHUB", "default")
    endpoint_url = os.getenv("DTS_ENDPOINT", "http://localhost:8080")
    
    logger.debug(f"Using DTS endpoint: {endpoint_url}")
    logger.debug(f"Using taskhub: {taskhub_name}")
    
    credential = None if endpoint_url.startswith("http://localhost") else DefaultAzureCredential()
    
    return DurableTaskSchedulerClient(
        host_address=endpoint_url,
        secure_channel=not endpoint_url.startswith("http://localhost"),
        taskhub=taskhub_name,
        token_credential=credential,
    )


def start_orchestration(client: DurableTaskSchedulerClient, alert: dict) -> str:
    """Start a fraud detection orchestration."""
    instance_id = client.schedule_new_orchestration(
        ORCHESTRATION_NAME,
        input=alert,
        instance_id=f"fraud-{alert['alert_id']}-{int(time.time())}",
    )
    logger.info(f"Started orchestration with instance ID: {instance_id}")
    return instance_id


def get_status(client: DurableTaskSchedulerClient, instance_id: str) -> OrchestrationState | None:
    """Get orchestration status."""
    return client.get_orchestration_state(instance_id)


def wait_for_status(
    client: DurableTaskSchedulerClient,
    instance_id: str,
    target_status: str = "RUNNING",
    timeout: int = 60,
    poll_interval: float = 1.0,
) -> OrchestrationState | None:
    """Wait for orchestration to reach a specific status."""
    start = time.time()
    while time.time() - start < timeout:
        state = get_status(client, instance_id)
        if state:
            current_status = state.runtime_status.name
            custom_status = state.custom_status or ""
            logger.debug(f"Status: {current_status}, Custom: {custom_status}")
            
            if current_status == target_status:
                return state
            
            if current_status in ("COMPLETED", "FAILED", "TERMINATED"):
                return state
        
        time.sleep(poll_interval)
    
    return None


def send_analyst_decision(
    client: DurableTaskSchedulerClient,
    instance_id: str,
    alert_id: str,
    action: str,
    notes: str = "",
    analyst_id: str = "analyst_cli",
) -> None:
    """Send analyst decision as external event."""
    decision = {
        "alert_id": alert_id,
        "approved_action": action,
        "analyst_notes": notes,
        "analyst_id": analyst_id,
    }
    
    logger.info(f"Sending analyst decision: {action}")
    client.raise_orchestration_event(
        instance_id=instance_id,
        event_name=ANALYST_APPROVAL_EVENT,
        data=decision,
    )
    logger.info("Decision sent successfully")


def print_result(state: OrchestrationState | None) -> None:
    """Print orchestration result."""
    if not state:
        logger.error("No state available")
        return
    
    print(f"\n{'='*60}")
    print("ORCHESTRATION RESULT")
    print(f"{'='*60}")
    print(f"Status: {state.runtime_status.name}")
    print(f"Custom Status: {state.serialized_custom_status or 'N/A'}")
    
    if state.serialized_output:
        try:
            result = json.loads(state.serialized_output)
            print(f"Alert ID: {result.get('alert_id')}")
            print(f"Risk Score: {result.get('risk_score', 'N/A')}")
            print(f"Action Taken: {result.get('action_taken', 'N/A')}")
            print(f"Success: {result.get('success', 'N/A')}")
        except json.JSONDecodeError:
            print(f"Output: {state.serialized_output}")
    
    print(f"{'='*60}\n")


# ============================================================================
# Test Scenarios
# ============================================================================


def test_high_risk_with_approval(client: DurableTaskSchedulerClient) -> None:
    """
    Test: High-risk alert → Analyst approves → Action executed
    """
    print("\n" + "="*70)
    print("TEST: High-Risk Alert with Analyst Approval")
    print("="*70)
    
    alert = SAMPLE_ALERTS["ALERT-001"]
    print(f"\nAlert: {alert['alert_id']} - {alert['alert_type']}")
    print(f"Description: {alert['description']}")
    
    # Start orchestration
    instance_id = start_orchestration(client, alert)
    
    # Wait for orchestration to request analyst review
    print("\n⏳ Waiting for analysis to complete and request analyst review...")
    
    for _ in range(120):  # Wait up to 2 minutes
        state = get_status(client, instance_id)
        if state:
            custom_status = state.serialized_custom_status or ""
            if "Awaiting analyst review" in custom_status:
                print(f"✓ Orchestration is waiting for analyst: {custom_status}")
                break
            if state.runtime_status.name in ("COMPLETED", "FAILED"):
                print(f"Orchestration ended: {state.runtime_status.name}")
                print_result(state)
                return
        time.sleep(1)
    else:
        print("⚠️ Timeout waiting for analyst review")
        return
    
    # Simulate analyst decision
    print("\n👤 Simulating analyst decision: lock_account")
    time.sleep(2)  # Simulate analyst thinking
    
    send_analyst_decision(
        client=client,
        instance_id=instance_id,
        alert_id=alert["alert_id"],
        action="lock_account",
        notes="Confirmed fraudulent activity - locking account",
        analyst_id="analyst_001",
    )
    
    # Wait for completion
    print("\n⏳ Waiting for orchestration to complete...")
    state = client.wait_for_orchestration_completion(instance_id, timeout=60)
    print_result(state)


def test_low_risk_auto_clear(client: DurableTaskSchedulerClient) -> None:
    """
    Test: Low-risk alert → Auto-cleared (no human review)
    """
    print("\n" + "="*70)
    print("TEST: Low-Risk Alert with Auto-Clear")
    print("="*70)
    
    # Modify alert to be low severity
    alert = {
        **SAMPLE_ALERTS["ALERT-002"],
        "severity": "low",
        "description": "Minor data usage increase - likely legitimate",
    }
    print(f"\nAlert: {alert['alert_id']} - {alert['alert_type']}")
    print(f"Description: {alert['description']}")
    
    # Start orchestration
    instance_id = start_orchestration(client, alert)
    
    # Wait for completion (should auto-clear)
    print("\n⏳ Waiting for orchestration to complete (should auto-clear)...")
    state = client.wait_for_orchestration_completion(instance_id, timeout=120)
    print_result(state)


def test_timeout_escalation(client: DurableTaskSchedulerClient) -> None:
    """
    Test: High-risk alert → Analyst doesn't respond → Timeout escalation
    """
    print("\n" + "="*70)
    print("TEST: Analyst Timeout Escalation")
    print("="*70)
    
    # Use very short timeout for demo
    alert = {
        **SAMPLE_ALERTS["ALERT-003"],
        "approval_timeout_hours": 0.001,  # ~3.6 seconds
    }
    print(f"\nAlert: {alert['alert_id']} - {alert['alert_type']}")
    print(f"Description: {alert['description']}")
    print(f"Timeout: {alert['approval_timeout_hours']*3600:.1f} seconds")
    
    # Start orchestration
    instance_id = start_orchestration(client, alert)
    
    # Wait for completion (will timeout and escalate)
    print("\n⏳ Waiting for timeout and escalation...")
    state = client.wait_for_orchestration_completion(instance_id, timeout=180)
    print_result(state)


def interactive_mode(client: DurableTaskSchedulerClient) -> None:
    """
    Interactive mode for manual testing.
    """
    print("\n" + "="*70)
    print("INTERACTIVE MODE")
    print("="*70)
    
    while True:
        print("\nOptions:")
        print("1. Start new orchestration (ALERT-001)")
        print("2. Start new orchestration (ALERT-002)")
        print("3. Start new orchestration (ALERT-003)")
        print("4. Check status of instance")
        print("5. Send analyst decision")
        print("6. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            instance_id = start_orchestration(client, SAMPLE_ALERTS["ALERT-001"])
            print(f"Instance ID: {instance_id}")
        
        elif choice == "2":
            instance_id = start_orchestration(client, SAMPLE_ALERTS["ALERT-002"])
            print(f"Instance ID: {instance_id}")
        
        elif choice == "3":
            instance_id = start_orchestration(client, SAMPLE_ALERTS["ALERT-003"])
            print(f"Instance ID: {instance_id}")
        
        elif choice == "4":
            instance_id = input("Instance ID: ").strip()
            state = get_status(client, instance_id)
            if state:
                print(f"Status: {state.runtime_status.name}")
                print(f"Custom: {state.custom_status}")
                if state.serialized_output:
                    print(f"Output: {state.serialized_output}")
            else:
                print("Not found")
        
        elif choice == "5":
            instance_id = input("Instance ID: ").strip()
            alert_id = input("Alert ID: ").strip()
            action = input("Action (lock_account/refund_charges/clear/both): ").strip()
            send_analyst_decision(client, instance_id, alert_id, action)
        
        elif choice == "6":
            break


# ============================================================================
# Main
# ============================================================================


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("Durable Fraud Detection Client")
    print("="*70)
    print("\nMake sure:")
    print("1. DTS emulator is running (docker)")
    print("2. Worker is running (python worker.py)")
    print("3. MCP server is running")
    print("")
    
    client = get_client()
    
    print("Select test mode:")
    print("1. Run automated tests")
    print("2. Interactive mode")
    
    choice = input("\nChoice: ").strip()
    
    if choice == "1":
        print("\nRunning automated tests...")
        
        # Test 1: High risk with approval
        test_high_risk_with_approval(client)
        
        # Test 2: Low risk auto-clear
        # test_low_risk_auto_clear(client)
        
        # Test 3: Timeout escalation
        # test_timeout_escalation(client)
        
        print("\n✅ All tests completed!")
    
    elif choice == "2":
        interactive_mode(client)
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
