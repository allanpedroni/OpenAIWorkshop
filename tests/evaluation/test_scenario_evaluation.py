"""
Scenario-Based Agent Evaluation

This module provides comprehensive evaluation for agents:
1. Goal-Based (Outcome): Did the user get what they needed? (LLM-as-Judge or keyword matching)
2. Process-Based (Tool Accuracy): Did the agent use the right tools? (LLM-as-Judge or F1 score)

Uses the AgentTestRunner for a consistent interface across all agents.
Optionally uses Azure AI Foundry LLM-as-Judge evaluators for more sophisticated evaluation.

Usage:
    cd tests/evaluation
    uv run pytest test_scenario_evaluation.py -v -s
    
    # With LLM-as-Judge (set EVAL_USE_LLM_JUDGE=true in .env)
    uv run pytest test_scenario_evaluation.py::TestAgentComparison -v -s
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pytest
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════════
# PATH SETUP
# ═══════════════════════════════════════════════════════════════════════════════

_eval_dir = Path(__file__).parent.resolve()
_tests_dir = _eval_dir.parent
_workspace_root = _tests_dir.parent
_agentic_ai_dir = _workspace_root / "agentic_ai"

sys.path.insert(0, str(_agentic_ai_dir))
sys.path.insert(0, str(_tests_dir))
sys.path.insert(0, str(_eval_dir))

load_dotenv(_eval_dir / ".env")

# Import the generic agent runner (ToolCallTracker is bundled in the runner)
from agent_runner import AgentTestRunner, QueryResult

# Import LLM judge evaluator
try:
    from llm_judge_evaluator import (
        LLMJudgeEvaluator,
        ToolCall,
        ToolDefinition,
        EvaluationResult,
        EVALUATORS_AVAILABLE,
    )
    LLM_JUDGE_AVAILABLE = EVALUATORS_AVAILABLE
except ImportError:
    LLM_JUDGE_AVAILABLE = False

# Check if LLM judge should be used
USE_LLM_JUDGE = os.getenv("EVAL_USE_LLM_JUDGE", "false").lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════════════════
# MCP TOOL DEFINITIONS (for LLM judge)
# ═══════════════════════════════════════════════════════════════════════════════

MCP_TOOL_DEFINITIONS = [
    {"name": "get_customer_detail", "description": "Get customer profile and account information"},
    {"name": "get_billing_summary", "description": "Get billing and invoice summary for a customer"},
    {"name": "get_subscription_detail", "description": "Get subscription plan details including data caps and features"},
    {"name": "get_data_usage", "description": "Get current data usage statistics"},
    {"name": "get_security_logs", "description": "Get security audit logs for account access attempts"},
    {"name": "unlock_account", "description": "Unlock a customer account after verification"},
    {"name": "get_products", "description": "List available products and add-ons"},
    {"name": "get_support_tickets", "description": "Get support ticket history"},
    {"name": "search_knowledge", "description": "Search the knowledge base for policies and procedures"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    user_message: str
    expected_tool_calls: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)  # Keywords in response


@dataclass
class Scenario:
    """A complete customer scenario for evaluation."""
    id: str
    name: str
    description: str
    customer_id: int
    
    # Conversation flow
    turns: list[ConversationTurn] = field(default_factory=list)
    
    # Expected tools across entire conversation
    expected_tools: list[str] = field(default_factory=list)
    
    # Expected outcome keywords (should appear in final response)
    success_keywords: list[str] = field(default_factory=list)
    
    # Expected resolution (for AI evaluation)
    expected_resolution: str = ""
    
    # Ground truth solution - the ideal/correct solution
    ground_truth_solution: str = ""
    
    # Scoring rubric - criteria for evaluating solution accuracy
    scoring_rubric: str = ""


# Define scenarios based on customer_scenarios.md and data_seeding.py
# MCP tool names: get_customer_detail, get_subscription_detail, get_data_usage, 
# get_billing_summary, get_security_logs, unlock_account, get_products, 
# search_knowledge, get_support_tickets, etc.
#
# Customer ID ranges:
# - 251-254: Documented scenarios from customer_scenarios.md
# - 1-50: Randomly generated customers in data_seeding.py (use for new scenarios)
SCENARIOS = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # BILLING & PAYMENT SCENARIOS (5 scenarios)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="billing_high_invoice",
        name="Invoice Higher Than Usual",
        description="Customer 251 has invoice $150, 2.5x the usual amount",
        customer_id=251,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 251. I noticed my last invoice was $150, which is much higher than usual. Can you help me understand why?",
                expected_tool_calls=["get_billing_summary", "get_data_usage"],
                expected_keywords=["invoice", "overage", "data", "usage"],
            ),
        ],
        expected_tools=[
            "get_customer_detail",
            "get_billing_summary",
            "get_subscription_detail",
            "get_data_usage",
            "search_knowledge",
        ],
        success_keywords=["overage", "data", "upgrade", "adjustment", "22", "10"],
        expected_resolution="Identify data overage (22GB vs 10GB cap), quote Data Overage Policy, offer adjustment or plan upgrade",
        ground_truth_solution="""The customer's invoice is $150 instead of the usual $60 because of data overage charges.
Key facts to communicate:
1. The customer's plan has a 10GB data cap
2. The customer used 22GB this billing cycle (12GB over the limit)
3. Overage charges of $7.50/GB apply per the Data Overage Policy
4. The additional $90 in charges (12GB x $7.50) explains the higher bill

Recommended solutions:
- Offer a one-time courtesy adjustment (if first offense)
- Recommend upgrading to a higher data plan or unlimited plan
- Set up data usage alerts to prevent future overages""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Correctly identifies overage (22GB vs 10GB), explains charges clearly, offers both adjustment AND upgrade options
4 - Good: Identifies overage and explains charges, offers at least one solution option
3 - Adequate: Identifies overage as the cause but missing specific numbers or only partial solution
2 - Poor: Vague explanation, doesn't clearly identify the cause or missing key details
1 - Fail: Incorrect explanation or completely unhelpful response""",
    ),
    
    Scenario(
        id="billing_payment_history",
        name="Payment History Inquiry",
        description="Customer wants to see recent payment history and payment methods",
        customer_id=5,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 5. Can you show me my recent payments? I want to make sure they all went through.",
                expected_tool_calls=["get_billing_summary"],
                expected_keywords=["payment", "successful", "history"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_billing_summary"],
        success_keywords=["payment", "successful", "credit_card", "amount", "date"],
        expected_resolution="Retrieve payment history and confirm successful payments",
        ground_truth_solution="""Show the customer their recent payment history.
Key information to provide:
1. List recent payments with dates and amounts
2. Confirm payment methods used (credit card, bank transfer, etc.)
3. Identify any failed or pending payments
4. Provide current account balance if any

Helpful actions:
- Confirm all payments were successful
- Mention autopay option if not enabled
- Offer to send payment receipt copies if needed""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows payment history with dates, amounts, methods, and confirms all went through
4 - Good: Shows payment history and confirms status
3 - Adequate: Provides payment information but incomplete details
2 - Poor: Vague response without specific payment details
1 - Fail: Doesn't provide payment information""",
    ),
    
    Scenario(
        id="billing_autopay_setup",
        name="Autopay Setup Request",
        description="Customer wants to enable automatic payments",
        customer_id=10,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 10. I keep forgetting to pay my bill on time. Can you help me set up autopay?",
                expected_tool_calls=["get_billing_summary", "search_knowledge"],
                expected_keywords=["autopay", "automatic", "payment"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_billing_summary", "get_subscription_detail", "search_knowledge"],
        success_keywords=["autopay", "automatic", "$5", "discount", "enable"],
        expected_resolution="Check current autopay status, explain autopay benefits including $5 discount, guide through setup",
        ground_truth_solution="""Help customer set up automatic payments.
Key information to provide:
1. Current autopay status (enabled or disabled)
2. Autopay includes a $5 monthly discount
3. Explain how autopay works (auto-charge on due date)

Required actions:
- Check current billing/subscription status
- Explain the $5 autopay discount
- Guide through the setup process
- Confirm payment method on file""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Checks status, mentions $5 discount, explains benefits, and guides through setup
4 - Good: Explains autopay benefits and how to set it up
3 - Adequate: Provides basic autopay information
2 - Poor: Generic response without checking account
1 - Fail: Doesn't help with autopay setup""",
    ),
    
    Scenario(
        id="billing_overdue_invoice",
        name="Overdue Invoice Question",
        description="Customer has overdue invoices and wants to understand implications",
        customer_id=15,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 15. I received a notice about an overdue invoice. What happens if I don't pay soon?",
                expected_tool_calls=["get_billing_summary"],
                expected_keywords=["overdue", "payment", "service"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_billing_summary", "search_knowledge"],
        success_keywords=["overdue", "payment", "suspension", "late", "fee"],
        expected_resolution="Show overdue invoices, explain late payment consequences, offer payment options",
        ground_truth_solution="""Address overdue invoice concerns.
Key information to provide:
1. List overdue invoices with amounts and due dates
2. Explain late fee policy (if applicable)
3. Potential service suspension after 30+ days overdue
4. Payment options available

Recommended actions:
- Show specific overdue amount
- Explain consequences (late fees, service suspension)
- Offer payment plan if large amount
- Process payment immediately if customer wants""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows overdue details, explains consequences, and offers solutions/payment options
4 - Good: Explains consequences and helps with payment
3 - Adequate: Addresses concern but missing specifics
2 - Poor: Generic response without checking account
1 - Fail: Doesn't address the overdue concern""",
    ),
    
    Scenario(
        id="billing_refund_request",
        name="Refund Request for Service Issue",
        description="Customer wants refund for days without service",
        customer_id=20,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 20. I was without internet for 3 days last week. Can I get a refund or credit for those days?",
                expected_tool_calls=["get_support_tickets", "get_billing_summary"],
                expected_keywords=["credit", "refund", "outage", "service"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_support_tickets", "get_subscription_detail", "get_billing_summary"],
        success_keywords=["credit", "refund", "outage", "days", "pro-rated"],
        expected_resolution="Verify outage via tickets/incidents, calculate pro-rated credit, apply to account",
        ground_truth_solution="""Process refund request for service outage.
Key information to verify:
1. Check support tickets for reported outage
2. Verify service incident records
3. Calculate pro-rated credit (3 days of monthly fee)

Recommended actions:
- Verify the outage occurred (via tickets or incidents)
- Calculate appropriate credit amount
- Apply credit to next invoice
- Apologize for the inconvenience
- Confirm credit will appear on next bill""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Verifies outage, calculates pro-rated credit, applies credit, and confirms
4 - Good: Acknowledges issue and offers appropriate credit
3 - Adequate: Offers to help with credit but missing verification
2 - Poor: Generic response without checking history
1 - Fail: Doesn't address the refund request""",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # INTERNET & CONNECTIVITY SCENARIOS (5 scenarios)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="internet_slow",
        name="Internet Slower Than Before",
        description="Customer 252 experiencing slow internet on 1Gbps tier",
        customer_id=252,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 252. My internet has been really slow lately. I'm paying for 1Gbps but it feels much slower.",
                expected_tool_calls=["get_subscription_detail", "get_support_tickets"],
                expected_keywords=["speed", "issue", "incident", "troubleshoot"],
            ),
        ],
        expected_tools=[
            "get_customer_detail",
            "get_subscription_detail",
            "get_support_tickets",
            "search_knowledge",
        ],
        success_keywords=["speed", "troubleshoot", "reboot", "test", "incident"],
        expected_resolution="Check subscription status, find open incident, provide troubleshooting steps",
        ground_truth_solution="""The customer is on a 1Gbps plan but experiencing slow speeds.
Key facts to communicate:
1. There is an existing open service incident affecting the customer's area
2. The incident was reported on April 17 and is still under investigation
3. The service status shows 'slow' indicating a known issue

Recommended actions:
- Acknowledge the known service issue and apologize for inconvenience
- Provide basic troubleshooting steps (restart router, check cables, test wired connection)
- Offer to create/escalate a support ticket for priority resolution
- Mention potential service credit once issue is resolved""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Identifies existing incident, provides troubleshooting steps, offers to escalate AND mentions potential credit
4 - Good: Identifies incident and provides troubleshooting, offers at least one proactive step
3 - Adequate: Acknowledges issue and provides some troubleshooting steps
2 - Poor: Generic troubleshooting without checking account status or incidents
1 - Fail: Unhelpful response or doesn't address the speed issue""",
    ),
    
    Scenario(
        id="internet_upgrade_inquiry",
        name="Internet Speed Upgrade Options",
        description="Customer wants to upgrade internet speed",
        customer_id=25,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 25. I work from home and my current internet is too slow for video calls. What upgrade options do I have?",
                expected_tool_calls=["get_subscription_detail", "get_products"],
                expected_keywords=["upgrade", "speed", "plan", "price"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products", "search_knowledge"],
        success_keywords=["upgrade", "Mbps", "Gbps", "Pro", "Ultimate", "price"],
        expected_resolution="Check current plan, show available upgrade options with pricing",
        ground_truth_solution="""Help customer upgrade their internet plan.
Key information to provide:
1. Current plan details (speed tier, price)
2. Available upgrade options:
   - Fiber Internet - Basic: 100 Mbps @ $49.99/month
   - Fiber Internet - Pro: 500 Mbps @ $79.99/month
   - Fiber Internet - Ultimate: 1 Gbps @ $119.99/month
3. For video calls, recommend at least Pro (500 Mbps)

Recommended actions:
- Show price difference from current plan
- Explain upgrade benefits (WiFi 6 router, priority support)
- Offer any applicable promotions (loyalty upgrade, new customer discount)
- Upgrades take effect within 24 hours""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows current plan, presents upgrade options with pricing, recommends based on need, mentions promotions
4 - Good: Shows options with pricing and makes recommendation
3 - Adequate: Lists upgrade options but missing personalization
2 - Poor: Generic product info without checking current plan
1 - Fail: Doesn't provide helpful upgrade information""",
    ),
    
    Scenario(
        id="internet_router_reset",
        name="Router Reset Help",
        description="Customer needs help resetting their router",
        customer_id=30,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 30. My router isn't working and I think I need to reset it. How do I do that?",
                expected_tool_calls=["search_knowledge"],
                expected_keywords=["reset", "button", "router"],
            ),
        ],
        expected_tools=["get_customer_detail", "search_knowledge"],
        success_keywords=["reset", "button", "10 seconds", "paperclip", "factory", "settings"],
        expected_resolution="Provide step-by-step router reset instructions from knowledge base",
        ground_truth_solution="""Help customer reset their router.
Steps to communicate:
1. Locate the reset button on the back of the router
2. Use a paperclip to press and hold the button for 10 seconds
3. Wait for the router to restart (lights will blink)
4. Router returns to factory settings
5. Reconnect using default WiFi name and password on router label

Additional help:
- If issues persist after reset, contact support at 1-800-CONTOSO
- Offer to schedule a technician if customer is uncomfortable doing it themselves""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Provides complete step-by-step instructions, mentions factory settings warning, offers additional help
4 - Good: Provides reset steps and basic guidance
3 - Adequate: Gives reset instructions but incomplete
2 - Poor: Vague instructions without specific steps
1 - Fail: Doesn't help with router reset""",
    ),
    
    Scenario(
        id="internet_outage_report",
        name="Internet Outage Report",
        description="Customer reporting complete internet outage",
        customer_id=35,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 35. My internet is completely down! Nothing is working. Is there an outage in my area?",
                expected_tool_calls=["get_subscription_detail", "get_support_tickets"],
                expected_keywords=["outage", "incident", "status"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_support_tickets", "search_knowledge"],
        success_keywords=["outage", "incident", "ticket", "technician", "status"],
        expected_resolution="Check for area outages, create support ticket if needed, provide ETA",
        ground_truth_solution="""Handle internet outage report.
Key actions:
1. Check subscription service status
2. Look for existing service incidents
3. Check if other support tickets exist for this customer

If outage confirmed:
- Apologize for the inconvenience
- Provide estimated restoration time
- Offer to notify when service is restored

If no known outage:
- Create a new support ticket
- Provide troubleshooting steps
- Offer technician visit if needed
- Mention service credit for extended outages""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Checks outage status, creates ticket if needed, provides ETA, offers follow-up
4 - Good: Checks status and takes appropriate action
3 - Adequate: Acknowledges issue and offers some help
2 - Poor: Generic response without checking system
1 - Fail: Doesn't address the outage report""",
    ),
    
    Scenario(
        id="internet_static_ip",
        name="Static IP Request",
        description="Customer needs a static IP address for work",
        customer_id=40,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 40. I need a static IP address for my home server. Do you offer that?",
                expected_tool_calls=["get_subscription_detail", "get_products"],
                expected_keywords=["static", "IP", "feature"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products"],
        success_keywords=["static", "IP", "Pro", "Ultimate", "upgrade", "feature"],
        expected_resolution="Check current plan, explain static IP is included in Pro/Ultimate plans",
        ground_truth_solution="""Help customer get a static IP address.
Key information:
1. Static IP is included in:
   - Fiber Internet - Pro ($79.99/month) - includes 1 static IP
   - Fiber Internet - Ultimate ($119.99/month) - includes 1 static IP
   - Business Internet - Enterprise ($299.99/month) - includes static IP block
2. Basic plan does not include static IP

Recommended actions:
- Check current plan
- If on Basic, recommend upgrade to Pro
- Explain static IP benefits and configuration
- Offer to process upgrade immediately""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Checks plan, explains which plans include static IP, recommends appropriate option
4 - Good: Explains static IP availability and recommends upgrade
3 - Adequate: Mentions static IP but missing plan details
2 - Poor: Generic response without specific information
1 - Fail: Doesn't address the static IP request""",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MOBILE & ROAMING SCENARIOS (4 scenarios)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="roaming_travel",
        name="Travelling Abroad - Needs Roaming",
        description="Customer 253 traveling to Spain, needs roaming setup",
        customer_id=253,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 253. I'm traveling to Spain in 2 days and need to know about international roaming.",
                expected_tool_calls=["get_subscription_detail", "get_products"],
                expected_keywords=["roaming", "international", "activate"],
            ),
        ],
        expected_tools=[
            "get_customer_detail",
            "get_subscription_detail",
            "get_products",
            "search_knowledge",
        ],
        success_keywords=["roaming", "international", "activate", "add-on"],
        expected_resolution="Check roaming not enabled, suggest International Roaming add-on, explain 3-day activation requirement",
        ground_truth_solution="""The customer needs international roaming enabled before traveling to Spain in 2 days.
Key facts to communicate:
1. International roaming is currently NOT enabled on their account
2. Roaming packages typically require 3 days to activate (customer is cutting it close)
3. Spain is covered under European roaming options
4. Available add-ons include voice, text, and data packages

Recommended actions:
- Urgently enable international roaming on the account
- Recommend appropriate roaming package for Spain (Europe zone)
- Warn about the activation timeline (may need to request expedited activation)
- Explain roaming rates and usage alerts to avoid bill shock""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Identifies roaming is off, explains urgency (3-day activation), offers to enable AND recommends specific package
4 - Good: Identifies roaming status and urgency, offers to enable roaming
3 - Adequate: Identifies roaming is not enabled and offers to help activate
2 - Poor: Generic roaming information without checking account status
1 - Fail: Doesn't address the roaming request or provides incorrect information""",
    ),
    
    Scenario(
        id="mobile_data_usage",
        name="Mobile Data Usage Check",
        description="Customer wants to check mobile data usage before cycle ends",
        customer_id=45,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 45. How much data have I used this month? I don't want to go over my limit.",
                expected_tool_calls=["get_data_usage", "get_subscription_detail"],
                expected_keywords=["data", "usage", "GB", "limit"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_data_usage", "get_subscription_detail"],
        success_keywords=["data", "used", "remaining", "GB", "cap"],
        expected_resolution="Show current data usage vs plan limit, warn if close to limit",
        ground_truth_solution="""Check customer's data usage.
Key information to provide:
1. Current data usage for this billing cycle
2. Data cap from subscription plan
3. Days remaining in billing cycle
4. Percentage of data used

If close to limit:
- Warn about overage charges
- Suggest data-saving tips
- Offer unlimited data upgrade option
- Explain how to set up usage alerts""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows usage, cap, remaining, and provides proactive advice based on status
4 - Good: Shows usage and limit with clear comparison
3 - Adequate: Provides data usage information
2 - Poor: Vague or incomplete information
1 - Fail: Doesn't provide data usage""",
    ),
    
    Scenario(
        id="mobile_upgrade_premium",
        name="Mobile Plan Upgrade",
        description="Customer wants to upgrade mobile plan for more data",
        customer_id=3,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 3. I keep running out of data. What mobile plans with more data do you have?",
                expected_tool_calls=["get_subscription_detail", "get_products"],
                expected_keywords=["plan", "unlimited", "data", "price"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products"],
        success_keywords=["Premium", "unlimited", "data", "59.99", "upgrade"],
        expected_resolution="Show current plan, recommend Mobile Plan - Premium with unlimited data",
        ground_truth_solution="""Help customer upgrade mobile plan.
Key information:
1. Current plan: Mobile Plan - Essential (5GB data @ $29.99/month)
2. Recommended upgrade: Mobile Plan - Premium ($59.99/month)
   - Unlimited data
   - International roaming included
   - 5G Priority
   - 50GB hotspot

Recommended actions:
- Explain price difference ($30/month more)
- Highlight unlimited data benefit
- Mention included international roaming
- Offer to process upgrade immediately""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows current plan, recommends Premium with pricing, highlights benefits
4 - Good: Provides upgrade options with clear comparison
3 - Adequate: Mentions upgrade options but missing details
2 - Poor: Generic product info without personalization
1 - Fail: Doesn't help with upgrade""",
    ),
    
    Scenario(
        id="mobile_hotspot_question",
        name="Mobile Hotspot Inquiry",
        description="Customer asking about hotspot feature on their plan",
        customer_id=8,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 8. Does my mobile plan include hotspot? I need to use it for my laptop.",
                expected_tool_calls=["get_subscription_detail"],
                expected_keywords=["hotspot", "plan", "feature"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products"],
        success_keywords=["hotspot", "included", "GB", "tethering"],
        expected_resolution="Check plan details, explain hotspot inclusion based on plan tier",
        ground_truth_solution="""Answer hotspot question.
Key information based on mobile plan:
- Essential plan: Hotspot NOT included (or limited)
- Premium plan: 50GB hotspot included

Actions:
- Check customer's current mobile plan
- Explain hotspot feature availability
- If not included, offer Premium upgrade
- Provide instructions on enabling hotspot if available""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Checks plan, explains hotspot status, provides usage info or upgrade option
4 - Good: Explains hotspot availability for their plan
3 - Adequate: Addresses hotspot question generally
2 - Poor: Vague response without checking plan
1 - Fail: Doesn't address hotspot question""",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ACCOUNT & SECURITY SCENARIOS (4 scenarios)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="account_locked",
        name="Account Locked After Failed Logins",
        description="Customer 254 locked out after multiple failed login attempts",
        customer_id=254,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 254. I can't log into my account - it says it's locked!",
                expected_tool_calls=["get_security_logs", "unlock_account"],
                expected_keywords=["locked", "security", "unlock", "password"],
            ),
        ],
        expected_tools=[
            "get_customer_detail",
            "get_security_logs",
            "unlock_account",
            "search_knowledge",
        ],
        success_keywords=["unlock", "password", "security", "2FA", "reset"],
        expected_resolution="Query security logs, verify identity, unlock account, recommend password reset and 2FA",
        ground_truth_solution="""The customer's account is locked due to multiple failed login attempts.
Key facts to communicate:
1. Security logs show multiple failed login attempts triggering automatic lockout
2. This is a security feature to protect the account
3. The account can be unlocked after identity verification

Required actions:
- Verify customer identity (already done via customer ID)
- Unlock the account using unlock_account tool
- Confirm the account is now accessible

Recommended follow-up:
- Suggest password reset if customer forgot password
- Recommend enabling 2FA for additional security
- Advise using password manager to prevent future lockouts""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Verifies identity, unlocks account, confirms success, AND provides security recommendations (password reset, 2FA)
4 - Good: Verifies identity, unlocks account, and provides at least one security recommendation
3 - Adequate: Unlocks the account and confirms it's accessible
2 - Poor: Attempts to help but doesn't actually unlock the account
1 - Fail: Doesn't address the lockout or provides incorrect instructions""",
    ),
    
    Scenario(
        id="account_security_check",
        name="Security Audit Request",
        description="Customer concerned about account security after hearing about data breaches",
        customer_id=12,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 12. I heard about data breaches in the news. Can you check if my account is secure?",
                expected_tool_calls=["get_security_logs"],
                expected_keywords=["security", "login", "access"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_security_logs", "search_knowledge"],
        success_keywords=["security", "login", "attempts", "2FA", "password"],
        expected_resolution="Review security logs, confirm no suspicious activity, recommend security best practices",
        ground_truth_solution="""Perform security audit for customer.
Key actions:
1. Review security logs for suspicious activity
2. Check for failed login attempts from unknown locations
3. Verify no unauthorized access

Provide security recommendations:
- Enable 2FA if not already enabled
- Use strong, unique password
- Update password every 90 days
- Never share credentials
- Monitor account for suspicious activity

Reassure customer and explain security measures in place.""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Reviews logs, reports findings, provides comprehensive security recommendations
4 - Good: Checks security status and provides recommendations
3 - Adequate: Reviews security but limited recommendations
2 - Poor: Generic security advice without checking account
1 - Fail: Doesn't address security concern""",
    ),
    
    Scenario(
        id="account_update_contact",
        name="Update Contact Information",
        description="Customer wants to update email and phone number",
        customer_id=18,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 18. I have a new email and phone number. Can you update my account information?",
                expected_tool_calls=["get_customer_detail"],
                expected_keywords=["update", "contact", "email", "phone"],
            ),
        ],
        expected_tools=["get_customer_detail"],
        success_keywords=["update", "email", "phone", "verify", "confirm"],
        expected_resolution="Show current info, explain update process, request new details",
        ground_truth_solution="""Help customer update contact information.
Key actions:
1. Retrieve current contact details
2. Verify customer identity
3. Collect new email and phone number
4. Explain verification process for new contact info

Security note:
- New email may require verification
- Update affects notifications and billing alerts
- Password reset links go to email on file
- Confirm all communication preferences""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows current info, requests new details, explains verification, updates preferences
4 - Good: Helps with update and explains process
3 - Adequate: Acknowledges request and provides guidance
2 - Poor: Generic response without checking current info
1 - Fail: Doesn't help with update""",
    ),
    
    Scenario(
        id="account_paperless_billing",
        name="Paperless Billing Setup",
        description="Customer wants to switch to paperless billing",
        customer_id=22,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 22. I want to go paperless and stop receiving paper bills. How do I do that?",
                expected_tool_calls=["get_customer_detail"],
                expected_keywords=["paperless", "email", "billing"],
            ),
        ],
        expected_tools=["get_customer_detail", "search_knowledge"],
        success_keywords=["paperless", "email", "billing", "enabled", "notification"],
        expected_resolution="Check current settings, enable paperless billing, confirm email on file",
        ground_truth_solution="""Enable paperless billing for customer.
Key actions:
1. Check current billing preferences
2. Verify email address on file
3. Enable paperless billing
4. Explain paperless billing benefits

Confirm:
- Bills will be sent to email on file
- Paper bills will stop within 1-2 billing cycles
- Can view all bills online anytime
- Email notifications for new bills""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Checks settings, confirms email, enables paperless, explains benefits
4 - Good: Enables paperless and confirms changes
3 - Adequate: Provides guidance on paperless billing
2 - Poor: Generic info without checking account
1 - Fail: Doesn't help with paperless setup""",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # TV & STREAMING SCENARIOS (2 scenarios)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="tv_channel_lineup",
        name="TV Channel Lineup Question",
        description="Customer asking about available channels on their TV plan",
        customer_id=28,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 28. What channels do I get with my TV streaming plan?",
                expected_tool_calls=["get_subscription_detail", "get_products"],
                expected_keywords=["channels", "TV", "streaming"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products"],
        success_keywords=["channels", "streaming", "screens", "replay"],
        expected_resolution="Check TV subscription, list included channels and features",
        ground_truth_solution="""Show TV streaming plan details.
TV Streaming plans:
- Basic ($34.99/month): 50+ channels, 2 screens, 7-day replay
- Premium ($64.99/month): 150+ channels, 4 screens, 30-day replay, sports, movies

Actions:
- Check current TV subscription
- List included channels/features
- Mention upgrade options if on Basic
- Explain how to access streaming app""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows plan details, lists features, mentions upgrade if applicable
4 - Good: Explains included channels and features
3 - Adequate: Provides plan information
2 - Poor: Generic TV info without checking plan
1 - Fail: Doesn't address channel question""",
    ),
    
    Scenario(
        id="tv_add_sports",
        name="Add Sports Package",
        description="Customer wants to add sports channels to TV plan",
        customer_id=32,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 32. I want to watch football games. Do you have a sports package I can add?",
                expected_tool_calls=["get_subscription_detail", "get_products"],
                expected_keywords=["sports", "package", "channels"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products"],
        success_keywords=["sports", "Premium", "channels", "upgrade"],
        expected_resolution="Check current TV plan, explain sports is in Premium, offer upgrade",
        ground_truth_solution="""Help customer add sports channels.
Key information:
- Sports package is included in TV Streaming - Premium ($64.99/month)
- Basic plan does not include sports channels

Actions:
- Check current TV subscription
- If on Basic, offer upgrade to Premium
- Premium includes sports package plus movie channels
- Also includes 4 screens and 30-day replay
- Calculate price difference from current plan""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Checks plan, explains sports in Premium, shows pricing, offers to upgrade
4 - Good: Explains sports availability and upgrade option
3 - Adequate: Mentions sports package info
2 - Poor: Generic info without checking current plan
1 - Fail: Doesn't help with sports request""",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # BUNDLE & PROMOTION SCENARIOS (3 scenarios)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="bundle_inquiry",
        name="Bundle Package Inquiry",
        description="Customer interested in bundling services",
        customer_id=38,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 38. I have internet and mobile separately. Would I save money if I bundle them?",
                expected_tool_calls=["get_subscription_detail", "get_products"],
                expected_keywords=["bundle", "save", "discount"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products"],
        success_keywords=["bundle", "Family Complete", "discount", "save", "$199.99"],
        expected_resolution="Show current services, calculate potential savings with bundle",
        ground_truth_solution="""Help customer understand bundle savings.
Bundle option:
- Bundle - Family Complete: $199.99/month
  - 500Mbps Internet
  - 150+ TV Channels
  - 2 Unlimited Mobile Lines
  - 20% discount vs individual services

Actions:
- Check current subscriptions and total cost
- Calculate potential savings with bundle
- Explain bundle includes more than current services
- Show value proposition
- Offer to switch to bundle if interested""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows current cost, calculates savings, explains bundle benefits, offers to switch
4 - Good: Explains bundle options and potential savings
3 - Adequate: Provides bundle information
2 - Poor: Generic bundle info without checking current services
1 - Fail: Doesn't help with bundle inquiry""",
    ),
    
    Scenario(
        id="promotion_eligibility",
        name="Promotion Eligibility Check",
        description="Customer asking about current promotions they qualify for",
        customer_id=42,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 42. Are there any promotions or discounts I'm eligible for?",
                expected_tool_calls=["get_customer_detail", "get_subscription_detail"],
                expected_keywords=["promotion", "discount", "offer"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_products"],
        success_keywords=["promotion", "discount", "loyalty", "offer", "eligible"],
        expected_resolution="Check loyalty level, current services, find applicable promotions",
        ground_truth_solution="""Check customer eligibility for promotions.
Available promotions:
1. New Customer - 20% Off (if new customer)
2. Bundle & Save - $50/month off (if 3+ services)
3. Loyalty Reward - Free speed upgrade (if Gold/Platinum)
4. Refer a Friend - $100 credit

Actions:
- Check loyalty level (Bronze/Silver/Gold/Platinum)
- Check number of active services
- Identify applicable promotions
- Explain how to take advantage of offers""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Checks eligibility, lists applicable promos, explains how to apply
4 - Good: Identifies promotions customer qualifies for
3 - Adequate: Mentions available promotions
2 - Poor: Generic promo list without checking eligibility
1 - Fail: Doesn't help with promotion inquiry""",
    ),
    
    Scenario(
        id="loyalty_benefits",
        name="Loyalty Program Benefits",
        description="Customer asking about loyalty program benefits",
        customer_id=48,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 48. I've been with you for years. What loyalty benefits do I get?",
                expected_tool_calls=["get_customer_detail"],
                expected_keywords=["loyalty", "benefits", "level"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_products", "search_knowledge"],
        success_keywords=["loyalty", "Gold", "Silver", "Platinum", "benefits", "upgrade"],
        expected_resolution="Check loyalty level, explain tier benefits, mention upgrade path",
        ground_truth_solution="""Show loyalty program benefits.
Loyalty tiers:
- Bronze: Basic support
- Silver: Priority support, occasional discounts
- Gold: 24/7 VIP support, free speed upgrades, special promotions
- Platinum: All Gold benefits plus dedicated account manager

Actions:
- Check customer's current loyalty level
- Explain benefits of their tier
- Mention how to reach next tier
- Highlight current Gold/Platinum promotion (free speed upgrade)""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Shows loyalty level, explains tier benefits, mentions upgrade path and current promos
4 - Good: Explains loyalty benefits for their tier
3 - Adequate: Provides loyalty program info
2 - Poor: Generic loyalty info without checking level
1 - Fail: Doesn't address loyalty question""",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SUPPORT TICKET SCENARIOS (2 scenarios)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="support_ticket_status",
        name="Support Ticket Status Check",
        description="Customer checking status of existing support ticket",
        customer_id=6,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 6. I opened a support ticket a few days ago. Can you check the status?",
                expected_tool_calls=["get_support_tickets"],
                expected_keywords=["ticket", "status", "open"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_support_tickets"],
        success_keywords=["ticket", "status", "open", "pending", "resolved"],
        expected_resolution="Find open tickets, provide status update, explain next steps",
        ground_truth_solution="""Check support ticket status.
Key actions:
1. Look up open/pending support tickets
2. Provide ticket number and status
3. Explain current stage of resolution
4. Provide expected resolution timeline

If ticket is pending:
- Explain what's being done
- Offer to escalate if delayed
- Provide contact for urgent issues""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Finds ticket, shows status, explains next steps, offers to escalate if needed
4 - Good: Provides ticket status and explanation
3 - Adequate: Finds and reports ticket status
2 - Poor: Generic response without checking tickets
1 - Fail: Doesn't help with ticket status""",
    ),
    
    Scenario(
        id="support_new_ticket",
        name="Create New Support Ticket",
        description="Customer wanting to open a new support ticket for equipment issue",
        customer_id=14,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 14. My cable box keeps rebooting randomly. I need someone to look at this.",
                expected_tool_calls=["get_subscription_detail", "get_support_tickets"],
                expected_keywords=["ticket", "equipment", "technician"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_support_tickets"],
        success_keywords=["ticket", "equipment", "technician", "issue", "scheduled"],
        expected_resolution="Document issue, create support ticket, offer technician visit",
        ground_truth_solution="""Handle equipment issue and create ticket.
Key actions:
1. Document the cable box issue (random reboots)
2. Check subscription for equipment details
3. Basic troubleshooting: unplug for 30 seconds, check connections
4. If issue persists, create support ticket

Support ticket should include:
- Equipment type and issue description
- Troubleshooting steps already attempted
- Priority level based on severity
- Offer technician visit if needed""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Documents issue, tries troubleshooting, creates ticket, offers technician
4 - Good: Creates ticket and offers resolution options
3 - Adequate: Acknowledges issue and offers to help
2 - Poor: Generic troubleshooting without creating ticket
1 - Fail: Doesn't address the equipment issue""",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MULTI-TURN SCENARIOS (5 scenarios with 2-4 turns each)
    # ═══════════════════════════════════════════════════════════════════════════════
    Scenario(
        id="multi_billing_dispute",
        name="[Multi-Turn] Billing Dispute Resolution",
        description="Customer disputes charge, agent investigates, customer asks for credit, then upgrade",
        customer_id=7,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 7. There's a $50 charge on my bill I don't recognize. What is this for?",
                expected_tool_calls=["get_billing_summary"],
                expected_keywords=["charge", "invoice", "billing"],
            ),
            ConversationTurn(
                user_message="I didn't order any equipment or additional services. Can you remove this charge?",
                expected_tool_calls=[],
                expected_keywords=["credit", "remove", "adjustment"],
            ),
            ConversationTurn(
                user_message="Thanks for the credit. While I have you, are there any promotions I qualify for?",
                expected_tool_calls=["get_customer_detail"],
                expected_keywords=["promotion", "discount", "offer"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_billing_summary", "get_subscription_detail"],
        success_keywords=["charge", "credit", "adjustment", "promotion", "discount"],
        expected_resolution="Investigate charge, apply credit if warranted, then check promotion eligibility",
        ground_truth_solution="""Multi-turn billing dispute resolution:

Turn 1 - Investigate the charge:
- Pull up billing summary to identify the $50 charge
- Explain what the charge is for (equipment fee, one-time charge, etc.)
- Show when it was applied

Turn 2 - Handle credit request:
- If charge is erroneous, apply credit
- If valid, explain why but offer goodwill credit if appropriate
- Confirm the adjustment will appear on next bill

Turn 3 - Check promotions:
- Review customer loyalty level and current services
- Identify applicable promotions
- Recommend best options based on their profile""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Investigates charge thoroughly, handles credit appropriately, provides personalized promotion info
4 - Good: Addresses each turn adequately with relevant information
3 - Adequate: Responds to each turn but missing depth or personalization
2 - Poor: Misses context between turns or provides generic responses
1 - Fail: Fails to address the dispute or loses conversation context""",
    ),
    
    Scenario(
        id="multi_internet_troubleshoot",
        name="[Multi-Turn] Internet Troubleshooting Flow",
        description="Step-by-step troubleshooting: check status, try fixes, escalate to technician",
        customer_id=16,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 16. My internet keeps dropping every few minutes. It's really frustrating.",
                expected_tool_calls=["get_subscription_detail", "get_support_tickets"],
                expected_keywords=["internet", "issue", "connection"],
            ),
            ConversationTurn(
                user_message="I already tried restarting the router. It worked for a bit but started dropping again.",
                expected_tool_calls=["search_knowledge"],
                expected_keywords=["troubleshoot", "check", "cable"],
            ),
            ConversationTurn(
                user_message="I checked the cables and they look fine. I think there might be something wrong with the equipment.",
                expected_tool_calls=[],
                expected_keywords=["technician", "appointment", "visit"],
            ),
            ConversationTurn(
                user_message="Yes, please schedule a technician. What times are available?",
                expected_tool_calls=[],
                expected_keywords=["scheduled", "appointment", "confirm"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_support_tickets", "search_knowledge"],
        success_keywords=["troubleshoot", "router", "cables", "technician", "appointment", "scheduled"],
        expected_resolution="Progressive troubleshooting leading to technician scheduling",
        ground_truth_solution="""Multi-turn troubleshooting flow:

Turn 1 - Initial diagnosis:
- Check subscription and service status
- Look for existing incidents or tickets
- Acknowledge the issue and express empathy

Turn 2 - Continue troubleshooting:
- Since router restart was tried, suggest next steps
- Check cable connections
- Try wired connection to isolate WiFi vs line issue
- Check for interference

Turn 3 - Escalate to technician:
- Acknowledge customer has tried basic troubleshooting
- Agree equipment may need inspection
- Offer to schedule technician visit

Turn 4 - Schedule appointment:
- Offer available time slots
- Confirm appointment details
- Provide technician arrival window
- Mention what technician will check""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Progressive troubleshooting, builds on previous turns, smooth escalation to technician
4 - Good: Addresses each step appropriately, schedules technician
3 - Adequate: Follows the flow but may skip steps or lack continuity
2 - Poor: Repetitive suggestions or doesn't build on previous attempts
1 - Fail: Doesn't progress logically or fails to schedule technician""",
    ),
    
    Scenario(
        id="multi_service_cancellation",
        name="[Multi-Turn] Service Cancellation Retention",
        description="Customer wants to cancel, agent attempts retention with offers",
        customer_id=24,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 24. I want to cancel my internet service. It's too expensive.",
                expected_tool_calls=["get_subscription_detail", "get_billing_summary"],
                expected_keywords=["cancel", "service", "understand"],
            ),
            ConversationTurn(
                user_message="I've been paying $119 a month and I found a competitor offering $70 for similar speeds.",
                expected_tool_calls=["get_products"],
                expected_keywords=["offer", "discount", "match", "retention"],
            ),
            ConversationTurn(
                user_message="A 20% discount sounds good. What would my new monthly rate be?",
                expected_tool_calls=[],
                expected_keywords=["$95", "monthly", "rate", "discount"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_subscription_detail", "get_billing_summary", "get_products"],
        success_keywords=["cancel", "retention", "discount", "offer", "rate", "save"],
        expected_resolution="Understand cancellation reason, offer retention discount, retain customer",
        ground_truth_solution="""Multi-turn retention flow:

Turn 1 - Understand cancellation reason:
- Pull up subscription details and billing
- Express understanding about cost concerns
- Ask about their specific needs
- Don't immediately accept cancellation

Turn 2 - Make retention offer:
- Acknowledge competitor pricing
- Check for available retention offers
- Offer 20% loyalty discount or price match
- Highlight value-adds (speed, reliability, support)

Turn 3 - Close the retention:
- Calculate new rate with discount ($119 × 0.8 = $95.20)
- Confirm the discount will be applied
- Explain discount duration (12 months, etc.)
- Thank customer for staying""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Empathetic handling, competitive retention offer, calculates new rate, secures retention
4 - Good: Makes appropriate retention offer and calculates savings
3 - Adequate: Attempts retention but may miss personalization or calculation
2 - Poor: Too quick to cancel or weak retention attempt
1 - Fail: Processes cancellation without retention effort""",
    ),
    
    Scenario(
        id="multi_new_customer_setup",
        name="[Multi-Turn] New Service Setup Assistance",
        description="Customer needs help choosing and setting up new services",
        customer_id=2,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 2. I just moved to a new apartment and need to set up internet. What are my options?",
                expected_tool_calls=["get_products"],
                expected_keywords=["internet", "plans", "options"],
            ),
            ConversationTurn(
                user_message="I work from home and need reliable internet for video calls. Which plan do you recommend?",
                expected_tool_calls=["get_subscription_detail"],
                expected_keywords=["Pro", "500Mbps", "recommend"],
            ),
            ConversationTurn(
                user_message="The Pro plan sounds good. Do you have any current promotions for new setups?",
                expected_tool_calls=[],
                expected_keywords=["promotion", "discount", "new customer"],
            ),
            ConversationTurn(
                user_message="Great! Please set me up with the Pro plan and the new customer discount.",
                expected_tool_calls=[],
                expected_keywords=["confirm", "order", "setup", "welcome"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_products", "get_subscription_detail"],
        success_keywords=["internet", "Pro", "500Mbps", "promotion", "discount", "setup", "order"],
        expected_resolution="Guide through plan selection, apply promotion, complete setup",
        ground_truth_solution="""Multi-turn new customer setup:

Turn 1 - Present options:
- List available internet plans (Basic, Pro, Ultimate)
- Explain speed tiers and pricing
- Ask about usage needs

Turn 2 - Make recommendation:
- For WFH with video calls, recommend Pro (500 Mbps)
- Explain why it's suitable (consistent speed, WiFi 6, priority support)
- Mention Ultimate if they want overkill

Turn 3 - Present promotions:
- New Customer 20% off first 3 months
- Mention WiFi 6 router included
- Explain installation options

Turn 4 - Complete setup:
- Confirm plan selection (Pro @ $79.99)
- Apply 20% promotion (first 3 months = $63.99)
- Set installation date
- Welcome to Contoso""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Natural sales flow, personalized recommendation, applies promo, completes setup smoothly
4 - Good: Guides through selection and setup with appropriate recommendations
3 - Adequate: Completes setup but may lack personalization or miss promotion
2 - Poor: Disjointed experience or missing key steps
1 - Fail: Doesn't complete the setup or loses track of conversation""",
    ),
    
    Scenario(
        id="multi_complex_account_issue",
        name="[Multi-Turn] Complex Account Resolution",
        description="Customer has multiple issues: wrong charge, slow internet, and needs plan change",
        customer_id=11,
        turns=[
            ConversationTurn(
                user_message="Hi, I'm customer 11. I have several issues. First, I was charged for a service I cancelled last month.",
                expected_tool_calls=["get_billing_summary", "get_subscription_detail"],
                expected_keywords=["charge", "cancelled", "billing"],
            ),
            ConversationTurn(
                user_message="Also, my internet has been slow for the past week. Are there any known issues?",
                expected_tool_calls=["get_support_tickets"],
                expected_keywords=["slow", "internet", "incident", "issue"],
            ),
            ConversationTurn(
                user_message="One more thing - I want to downgrade my TV package. I don't watch that much anymore.",
                expected_tool_calls=["get_products"],
                expected_keywords=["downgrade", "TV", "package", "change"],
            ),
            ConversationTurn(
                user_message="Can you summarize all the changes you're making to my account?",
                expected_tool_calls=[],
                expected_keywords=["summary", "credit", "downgrade", "changes"],
            ),
        ],
        expected_tools=["get_customer_detail", "get_billing_summary", "get_subscription_detail", "get_support_tickets", "get_products"],
        success_keywords=["credit", "refund", "slow", "incident", "downgrade", "TV", "summary", "changes"],
        expected_resolution="Handle billing credit, check internet issue, process TV downgrade, summarize all changes",
        ground_truth_solution="""Multi-turn complex account resolution:

Turn 1 - Billing issue:
- Check billing for the cancelled service charge
- Identify the erroneous charge
- Apply credit/refund for the amount
- Confirm it will be removed

Turn 2 - Internet issue:
- Check for service incidents
- Check subscription service status
- If incident exists, provide status and ETA
- If not, offer troubleshooting

Turn 3 - TV downgrade:
- Show current TV package
- Explain downgrade options (Premium to Basic)
- Calculate savings
- Process the change

Turn 4 - Summary:
- Recap all changes made:
  1. Credit applied for erroneous charge: $X
  2. Internet issue: status/resolution
  3. TV downgrade: from Premium to Basic, saving $X/month
- Confirm customer is satisfied""",
        scoring_rubric="""Score 1-5 based on these criteria:
5 - Excellent: Handles all 3 issues effectively, provides clear summary, maintains context throughout
4 - Good: Addresses all issues with reasonable resolution
3 - Adequate: Handles most issues but may miss one or lack cohesive summary
2 - Poor: Loses track of issues or provides incomplete resolution
1 - Fail: Unable to handle multiple issues or forgets earlier requests""",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO EVALUATOR (Using AgentTestRunner)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ScenarioResult:
    """Complete result from running a scenario."""
    scenario: Scenario
    agent_name: str
    query_results: list[QueryResult] = field(default_factory=list)
    total_time: float = 0.0
    
    # Tool-based metrics (Process Evaluation) - Rule-based F1
    tool_recall: float = 0.0      # % of expected tools called
    tool_precision: float = 0.0   # % of called tools that were expected
    tool_f1: float = 0.0          # Harmonic mean of precision and recall
    
    # Outcome-based metrics (Goal Evaluation) - Keyword matching fallback
    keyword_coverage: float = 0.0  # % of success keywords in response
    response_length: int = 0       # Total response length
    
    # LLM-as-Judge metrics (Azure AI Foundry)
    llm_intent_score: Optional[float] = None      # 1-5: Did agent understand intent?
    llm_intent_result: Optional[str] = None       # "pass" or "fail"
    llm_intent_reason: Optional[str] = None
    llm_task_score: Optional[float] = None        # 1-5: Did response follow task?
    llm_task_result: Optional[str] = None
    llm_task_reason: Optional[str] = None
    llm_tool_score: Optional[float] = None        # 1-5: Were correct tools called?
    llm_tool_result: Optional[str] = None
    llm_coherence: Optional[float] = None         # 1-5: Is response coherent?
    llm_fluency: Optional[float] = None           # 1-5: Is language natural?
    llm_relevance: Optional[float] = None         # 1-5: Is response relevant?
    llm_solution_score: Optional[float] = None    # 1-5: Solution accuracy vs ground truth
    llm_solution_reason: Optional[str] = None     # Explanation of solution score
    llm_eval_time: float = 0.0
    llm_errors: list[str] = field(default_factory=list)
    
    # Overall
    success: bool = False
    
    def compute_metrics(self):
        """Compute both tool accuracy and outcome metrics (rule-based)."""
        # Collect all tools and responses
        all_tools_called = set()
        all_responses = []
        
        for qr in self.query_results:
            all_tools_called.update(qr.tool_calls)
            all_responses.append(qr.response.lower())
        
        combined_response = " ".join(all_responses)
        self.response_length = len(combined_response)
        
        # ─────────────────────────────────────────────────────────────────────
        # TOOL ACCURACY (Process-Based) - Rule-based F1
        # ─────────────────────────────────────────────────────────────────────
        expected_tools = set(self.scenario.expected_tools)
        
        if expected_tools:
            # Recall: What % of expected tools were called?
            self.tool_recall = len(all_tools_called & expected_tools) / len(expected_tools)
        
        if all_tools_called:
            # Precision: What % of called tools were expected?
            self.tool_precision = len(all_tools_called & expected_tools) / len(all_tools_called)
        
        # F1 Score: Harmonic mean
        if self.tool_precision + self.tool_recall > 0:
            self.tool_f1 = 2 * (self.tool_precision * self.tool_recall) / (self.tool_precision + self.tool_recall)
        
        # ─────────────────────────────────────────────────────────────────────
        # KEYWORD COVERAGE (Outcome-Based) - Fallback when LLM judge not used
        # ─────────────────────────────────────────────────────────────────────
        if self.scenario.success_keywords:
            found = sum(1 for kw in self.scenario.success_keywords if kw.lower() in combined_response)
            self.keyword_coverage = found / len(self.scenario.success_keywords)
        
        # ─────────────────────────────────────────────────────────────────────
        # SUCCESS CRITERIA
        # ─────────────────────────────────────────────────────────────────────
        # If LLM judge was used, use its results
        if self.llm_intent_result is not None or self.llm_task_result is not None:
            # LLM-based success: intent resolved or task adhered
            llm_passes = []
            if self.llm_intent_result:
                llm_passes.append(self.llm_intent_result == "pass")
            if self.llm_task_result:
                llm_passes.append(self.llm_task_result == "pass")
            self.success = any(llm_passes) if llm_passes else self.keyword_coverage >= 0.5
        else:
            # Keyword-based success
            has_no_errors = all(qr.error is None for qr in self.query_results)
            self.success = self.keyword_coverage >= 0.5 and has_no_errors
    
    async def compute_llm_metrics(self, evaluator: "LLMJudgeEvaluator"):
        """Compute LLM-as-Judge metrics using Azure AI Foundry evaluators."""
        if not self.query_results:
            return
        
        # Get the query and response
        query = self.scenario.turns[0].user_message if self.scenario.turns else ""
        response = self.query_results[-1].response if self.query_results else ""
        
        # Get tool calls from all turns
        all_tool_calls = []
        for qr in self.query_results:
            for tool_name in qr.tool_calls:
                all_tool_calls.append(ToolCall(name=tool_name))
        
        # Convert MCP tool definitions
        tool_defs = [
            ToolDefinition(name=td["name"], description=td["description"])
            for td in MCP_TOOL_DEFINITIONS
        ]
        
        # Run LLM evaluation
        try:
            result = await evaluator.evaluate(
                query=query,
                response=response,
                tool_calls=all_tool_calls,
                tool_definitions=tool_defs,
                ground_truth_solution=self.scenario.ground_truth_solution,
                scoring_rubric=self.scenario.scoring_rubric,
            )
            
            # Copy results
            self.llm_intent_score = result.intent_resolution_score
            self.llm_intent_result = result.intent_resolution_result
            self.llm_intent_reason = result.intent_resolution_reason
            self.llm_task_score = result.task_adherence_score
            self.llm_task_result = result.task_adherence_result
            self.llm_task_reason = result.task_adherence_reason
            self.llm_tool_score = result.tool_call_accuracy_score
            self.llm_tool_result = result.tool_call_accuracy_result
            self.llm_coherence = result.coherence_score
            self.llm_fluency = result.fluency_score
            self.llm_relevance = result.relevance_score
            self.llm_solution_score = result.solution_accuracy_score
            self.llm_solution_reason = result.solution_accuracy_reason
            self.llm_eval_time = result.evaluation_time
            self.llm_errors = result.errors
            
        except Exception as e:
            self.llm_errors.append(f"LLM evaluation failed: {e}")


class ScenarioEvaluator:
    """
    Runs scenarios against any agent using the generic AgentTestRunner.
    Evaluates both tool accuracy and outcome quality.
    
    Supports two evaluation modes:
    1. Rule-based (default): Tool F1 + keyword matching
    2. LLM-as-Judge: Azure AI Foundry evaluators (IntentResolution, TaskAdherence, etc.)
    """
    
    def __init__(
        self,
        agent_name: str = "single",
        use_llm_judge: bool = None,
        enable_quality_metrics: bool = True,
    ):
        """
        Args:
            agent_name: Agent shorthand ("single", "reflection", "handoff", "magentic")
                       or full module path
            use_llm_judge: Use LLM-as-Judge evaluators (default: from env var)
            enable_quality_metrics: Include coherence, fluency, relevance (slower)
        """
        self.agent_name = agent_name
        self.runner = AgentTestRunner(agent_name)
        
        # Determine if LLM judge should be used
        if use_llm_judge is None:
            use_llm_judge = USE_LLM_JUDGE and LLM_JUDGE_AVAILABLE
        
        self.use_llm_judge = use_llm_judge
        self.enable_quality_metrics = enable_quality_metrics
        self.llm_evaluator = None
        
        if self.use_llm_judge and LLM_JUDGE_AVAILABLE:
            self.llm_evaluator = LLMJudgeEvaluator(
                enable_agent_evaluators=True,
                enable_quality_evaluators=enable_quality_metrics,
            )
            print(f"  [LLM] LLM-as-Judge: ENABLED")
        else:
            print(f"  [RULE] LLM-as-Judge: DISABLED (using keyword matching)")
    
    async def run_scenario(self, scenario: Scenario) -> ScenarioResult:
        """Run a complete scenario and return results."""
        result = ScenarioResult(scenario=scenario, agent_name=self.agent_name)
        
        start_time = time.time()
        
        # Run each turn in the scenario
        for turn in scenario.turns:
            query_result = await self.runner.run_query(turn.user_message)
            result.query_results.append(query_result)
        
        result.total_time = time.time() - start_time
        
        # Compute rule-based metrics first
        result.compute_metrics()
        
        # Optionally run LLM judge evaluation
        if self.llm_evaluator is not None:
            await result.compute_llm_metrics(self.llm_evaluator)
            # Recompute success based on LLM results
            result.compute_metrics()
        
        return result
    
    async def run_all_scenarios(
        self,
        scenarios: list[Scenario] | None = None,
        verbose: bool = True,
    ) -> list[ScenarioResult]:
        """Run all scenarios and return results."""
        scenarios = scenarios or SCENARIOS
        results = []
        
        for scenario in scenarios:
            if verbose:
                print(f"\n[{self.agent_name}] Running: {scenario.name}")
            
            result = await self.run_scenario(scenario)
            results.append(result)
            
            if verbose:
                status = "✅" if result.success else "❌"
                
                # Show different metrics based on evaluation mode
                if result.llm_intent_score is not None:
                    # LLM judge mode
                    intent = f"Intent: {result.llm_intent_score:.0f}/5" if result.llm_intent_score else "Intent: N/A"
                    task = f"Task: {result.llm_task_score:.0f}/5" if result.llm_task_score else "Task: N/A"
                    print(f"  {status} {intent}, {task}, Time: {result.total_time:.1f}s (+{result.llm_eval_time:.1f}s eval)")
                else:
                    # Keyword mode
                    print(f"  {status} Tool F1: {result.tool_f1:.1%}, "
                          f"Keywords: {result.keyword_coverage:.1%}, "
                          f"Time: {result.total_time:.1f}s")
        
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARISON REPORT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AgentSummary:
    """Aggregated metrics for an agent across all scenarios."""
    agent_name: str
    scenarios_passed: int = 0
    scenarios_total: int = 0
    
    # Rule-based metrics
    avg_tool_recall: float = 0.0
    avg_tool_precision: float = 0.0
    avg_tool_f1: float = 0.0
    avg_keyword_coverage: float = 0.0
    
    # LLM-as-Judge metrics
    avg_intent_score: Optional[float] = None
    avg_task_score: Optional[float] = None
    avg_tool_score: Optional[float] = None
    avg_coherence: Optional[float] = None
    avg_fluency: Optional[float] = None
    avg_relevance: Optional[float] = None
    avg_solution_score: Optional[float] = None  # Solution accuracy vs ground truth
    intent_pass_rate: float = 0.0
    task_pass_rate: float = 0.0
    solution_pass_rate: float = 0.0  # % with solution score >= 3
    
    avg_time: float = 0.0
    total_tools_called: int = 0
    uses_llm_judge: bool = False
    
    @classmethod
    def from_results(cls, agent_name: str, results: list[ScenarioResult]) -> "AgentSummary":
        if not results:
            return cls(agent_name=agent_name)
        
        n = len(results)
        
        # Check if LLM judge was used
        has_llm = any(r.llm_intent_score is not None for r in results)
        
        summary = cls(
            agent_name=agent_name,
            scenarios_passed=sum(1 for r in results if r.success),
            scenarios_total=n,
            avg_tool_recall=sum(r.tool_recall for r in results) / n,
            avg_tool_precision=sum(r.tool_precision for r in results) / n,
            avg_tool_f1=sum(r.tool_f1 for r in results) / n,
            avg_keyword_coverage=sum(r.keyword_coverage for r in results) / n,
            avg_time=sum(r.total_time for r in results) / n,
            total_tools_called=sum(len(qr.tool_calls) for r in results for qr in r.query_results),
            uses_llm_judge=has_llm,
        )
        
        # Compute LLM judge averages if available
        if has_llm:
            intent_scores = [r.llm_intent_score for r in results if r.llm_intent_score is not None]
            task_scores = [r.llm_task_score for r in results if r.llm_task_score is not None]
            tool_scores = [r.llm_tool_score for r in results if r.llm_tool_score is not None]
            coherence = [r.llm_coherence for r in results if r.llm_coherence is not None]
            fluency = [r.llm_fluency for r in results if r.llm_fluency is not None]
            relevance = [r.llm_relevance for r in results if r.llm_relevance is not None]
            solution_scores = [r.llm_solution_score for r in results if r.llm_solution_score is not None]
            
            if intent_scores:
                summary.avg_intent_score = sum(intent_scores) / len(intent_scores)
            if task_scores:
                summary.avg_task_score = sum(task_scores) / len(task_scores)
            if tool_scores:
                summary.avg_tool_score = sum(tool_scores) / len(tool_scores)
            if coherence:
                summary.avg_coherence = sum(coherence) / len(coherence)
            if fluency:
                summary.avg_fluency = sum(fluency) / len(fluency)
            if relevance:
                summary.avg_relevance = sum(relevance) / len(relevance)
            if solution_scores:
                summary.avg_solution_score = sum(solution_scores) / len(solution_scores)
                # Pass rate: score >= 3 (Adequate or better)
                summary.solution_pass_rate = sum(1 for s in solution_scores if s >= 3) / len(solution_scores)
            
            # Pass rates
            intent_passes = [r for r in results if r.llm_intent_result == "pass"]
            task_passes = [r for r in results if r.llm_task_result == "pass"]
            summary.intent_pass_rate = len(intent_passes) / n
            summary.task_pass_rate = len(task_passes) / n
        
        return summary


def generate_comparison_report(
    results_by_agent: dict[str, list[ScenarioResult]],
) -> str:
    """Generate a comprehensive comparison report."""
    
    # Check if LLM judge was used
    first_results = list(results_by_agent.values())[0]
    uses_llm = any(r.llm_intent_score is not None for r in first_results)
    
    mode = "LLM-as-Judge (Azure AI Foundry)" if uses_llm else "Rule-Based (Tool F1 + Keywords)"
    
    lines = [
        "",
        "═" * 90,
        f"AGENT EVALUATION REPORT: {mode}",
        "═" * 90,
    ]
    
    # Get agent names
    agent_names = list(results_by_agent.keys())
    
    # Per-scenario breakdown
    lines.extend([
        "",
        "SCENARIO BREAKDOWN",
        "-" * 90,
    ])
    
    if uses_llm:
        lines.append(f"{'Scenario':<28} {'Agent':<12} {'Pass':<6} {'Intent':<8} {'Solution':<10} {'Time':<8}")
    else:
        lines.append(f"{'Scenario':<28} {'Agent':<12} {'Pass':<6} {'Tool F1':<10} {'Keywords':<10} {'Time':<8}")
    
    lines.append("-" * 90)
    
    # Assume all agents ran same scenarios in same order
    first_agent_results = results_by_agent[agent_names[0]]
    
    for i, scenario in enumerate([r.scenario for r in first_agent_results]):
        scenario_name = scenario.name[:26]
        
        for agent_name in agent_names:
            result = results_by_agent[agent_name][i]
            status = "✅" if result.success else "❌"
            
            if uses_llm:
                intent = f"{result.llm_intent_score:.0f}/5" if result.llm_intent_score else "N/A"
                solution = f"{result.llm_solution_score:.0f}/5" if result.llm_solution_score else "N/A"
                lines.append(
                    f"{scenario_name:<28} {agent_name:<12} {status:<6} "
                    f"{intent:<8} {solution:<10} {result.total_time:>6.1f}s"
                )
            else:
                lines.append(
                    f"{scenario_name:<28} {agent_name:<12} {status:<6} "
                    f"{result.tool_f1:>8.1%} {result.keyword_coverage:>10.1%} "
                    f"{result.total_time:>6.1f}s"
                )
        
        lines.append("")  # Space between scenarios
    
    # Summary statistics
    lines.extend([
        "-" * 90,
        "SUMMARY",
        "-" * 90,
        "",
    ])
    
    # Header with agent names
    header = f"{'Metric':<30}"
    for name in agent_names:
        header += f" {name:>15}"
    lines.append(header)
    lines.append("-" * (30 + 16 * len(agent_names)))
    
    # Compute summaries
    summaries = {name: AgentSummary.from_results(name, results) 
                 for name, results in results_by_agent.items()}
    
    # Metrics rows - different based on mode
    if uses_llm:
        metrics = [
            ("Scenarios Passed", lambda s: f"{s.scenarios_passed}/{s.scenarios_total}"),
            ("Solution Pass Rate (>=3)", lambda s: f"{s.solution_pass_rate:.1%}" if s.avg_solution_score else "N/A"),
            ("Avg Solution Score", lambda s: f"{s.avg_solution_score:.1f}/5" if s.avg_solution_score else "N/A"),
            ("Avg Intent Score", lambda s: f"{s.avg_intent_score:.1f}/5" if s.avg_intent_score else "N/A"),
            ("Avg Coherence", lambda s: f"{s.avg_coherence:.1f}/5" if s.avg_coherence else "N/A"),
            ("Avg Fluency", lambda s: f"{s.avg_fluency:.1f}/5" if s.avg_fluency else "N/A"),
            ("Avg Relevance", lambda s: f"{s.avg_relevance:.1f}/5" if s.avg_relevance else "N/A"),
            ("Avg Time (s)", lambda s: f"{s.avg_time:.1f}"),
            ("Total Tools Called", lambda s: f"{s.total_tools_called}"),
        ]
    else:
        metrics = [
            ("Scenarios Passed", lambda s: f"{s.scenarios_passed}/{s.scenarios_total}"),
            ("Avg Tool Recall", lambda s: f"{s.avg_tool_recall:.1%}"),
            ("Avg Tool Precision", lambda s: f"{s.avg_tool_precision:.1%}"),
            ("Avg Tool F1", lambda s: f"{s.avg_tool_f1:.1%}"),
            ("Avg Keyword Coverage", lambda s: f"{s.avg_keyword_coverage:.1%}"),
            ("Avg Time (s)", lambda s: f"{s.avg_time:.1f}"),
            ("Total Tools Called", lambda s: f"{s.total_tools_called}"),
        ]
    
    for metric_name, formatter in metrics:
        row = f"{metric_name:<30}"
        for name in agent_names:
            row += f" {formatter(summaries[name]):>15}"
        lines.append(row)
    
    lines.extend(["", "═" * 90, ""])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# PYTEST TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def single_evaluator():
    return ScenarioEvaluator(agent_name="single")


@pytest.fixture
def reflection_evaluator():
    return ScenarioEvaluator(agent_name="reflection")


class TestScenarioEvaluation:
    """Scenario-based evaluation tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_single_scenario_billing(self, single_evaluator):
        """Test single agent on billing scenario."""
        scenario = SCENARIOS[0]  # billing_high_invoice
        result = await single_evaluator.run_scenario(scenario)
        
        print(f"\nScenario: {scenario.name}")
        print(f"Response: {result.query_results[0].response[:300]}...")
        print(f"Tools called: {result.query_results[0].tool_calls}")
        print(f"Tool F1: {result.tool_f1:.1%}")
        print(f"Keyword coverage: {result.keyword_coverage:.1%}")
        
        assert result.keyword_coverage >= 0.3, "Should mention some relevant keywords"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_all_scenarios_single_agent(self, single_evaluator):
        """Run all scenarios with single agent."""
        results = await single_evaluator.run_all_scenarios()
        
        passed = sum(1 for r in results if r.success)
        print(f"\nSingle Agent: {passed}/{len(results)} scenarios passed")
        
        assert passed >= len(results) // 2, "At least half of scenarios should pass"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_all_scenarios_reflection_agent(self, reflection_evaluator):
        """Run all scenarios with reflection agent."""
        results = await reflection_evaluator.run_all_scenarios()
        
        passed = sum(1 for r in results if r.success)
        print(f"\nReflection Agent: {passed}/{len(results)} scenarios passed")
        
        assert passed >= len(results) // 2, "At least half of scenarios should pass"


class TestAgentComparison:
    """Compare multiple agents on all scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_compare_single_vs_reflection(self):
        """Compare single vs reflection agent with full metrics."""
        agents = ["single", "reflection"]
        results_by_agent: dict[str, list[ScenarioResult]] = {}
        
        for agent_name in agents:
            print(f"\n{'=' * 40}")
            print(f"Running {agent_name} agent...")
            print("=" * 40)
            
            evaluator = ScenarioEvaluator(agent_name=agent_name)
            results = await evaluator.run_all_scenarios()
            results_by_agent[agent_name] = results
        
        # Generate and print report
        report = generate_comparison_report(results_by_agent)
        print(report)
        
        # Save results
        results_file = _eval_dir / "agent_comparison_results.json"
        _save_results(results_by_agent, results_file)
        
        print(f"\nResults saved to: {results_file}")
        
        # Basic assertions
        for agent_name, results in results_by_agent.items():
            passed = sum(1 for r in results if r.success)
            assert passed >= 1, f"{agent_name} should pass at least 1 scenario"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_compare_all_agents_parallel(self):
        """Compare ALL agents in parallel for speed."""
        # Available agents: single, reflection, handoff, magentic
        # Note: magentic excluded due to tool call tracking issues
        agents = ["single", "reflection", "handoff"]
        
        async def run_agent(agent_name: str) -> tuple[str, list[ScenarioResult]]:
            """Run single agent evaluation."""
            print(f"\n[{agent_name}] Starting evaluation...")
            evaluator = ScenarioEvaluator(agent_name=agent_name)
            results = await evaluator.run_all_scenarios()
            passed = sum(1 for r in results if r.success)
            print(f"[{agent_name}] Completed: {passed}/{len(results)} passed")
            return agent_name, results
        
        # Run all agents in parallel
        print("\n" + "=" * 60)
        print("RUNNING ALL AGENTS IN PARALLEL")
        print("=" * 60)
        
        import time
        start_time = time.time()
        
        # Execute all agents concurrently
        tasks = [run_agent(agent_name) for agent_name in agents]
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Collect results (filter out exceptions)
        results_by_agent: dict[str, list[ScenarioResult]] = {}
        for result in agent_results:
            if isinstance(result, Exception):
                print(f"Agent failed with error: {result}")
            else:
                agent_name, results = result
                results_by_agent[agent_name] = results
        
        # Generate and print report
        if results_by_agent:
            report = generate_comparison_report(results_by_agent)
            print(report)
            
            print(f"\nTotal parallel execution time: {total_time:.1f}s")
            print(f"(Sequential would be ~{total_time * len(agents):.1f}s)")
        
        # Save results
        results_file = _eval_dir / "all_agents_comparison.json"
        _save_results(results_by_agent, results_file)
        print(f"\nResults saved to: {results_file}")
        
        # Basic assertions
        assert len(results_by_agent) >= 2, "At least 2 agents should complete"
        for agent_name, results in results_by_agent.items():
            passed = sum(1 for r in results if r.success)
            assert passed >= 1, f"{agent_name} should pass at least 1 scenario"


def _save_results(results_by_agent: dict[str, list[ScenarioResult]], results_file: Path):
    """Save evaluation results to JSON file."""
    with open(results_file, "w") as f:
        json.dump({
            agent_name: [
                {
                    "scenario": r.scenario.id,
                    "scenario_name": r.scenario.name,
                    "success": r.success,
                    # Rule-based metrics
                    "tool_recall": r.tool_recall,
                    "tool_precision": r.tool_precision,
                    "tool_f1": r.tool_f1,
                    "keyword_coverage": r.keyword_coverage,
                    "total_time": r.total_time,
                    "tools_called": [tc for qr in r.query_results for tc in qr.tool_calls],
                    # LLM-as-Judge metrics
                    "llm_intent_score": r.llm_intent_score,
                    "llm_intent_result": r.llm_intent_result,
                    "llm_intent_reason": r.llm_intent_reason,
                    "llm_task_score": r.llm_task_score,
                    "llm_task_result": r.llm_task_result,
                    "llm_task_reason": r.llm_task_reason,
                    "llm_tool_score": r.llm_tool_score,
                    "llm_coherence": r.llm_coherence,
                    "llm_fluency": r.llm_fluency,
                    "llm_relevance": r.llm_relevance,
                    "llm_solution_score": r.llm_solution_score,
                    "llm_solution_reason": r.llm_solution_reason,
                    "llm_eval_time": r.llm_eval_time,
                }
                for r in results
            ]
            for agent_name, results in results_by_agent.items()
        }, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import logging
    import warnings
    
    # Suppress MCP client cleanup warnings
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    async def main():
        print("Agent Evaluation: Tool Accuracy + Outcome Quality")
        print("=" * 60)
        
        agents = ["single", "reflection"]
        results_by_agent: dict[str, list[ScenarioResult]] = {}
        
        for agent_name in agents:
            print(f"\n{'─' * 40}")
            print(f"Running {agent_name} agent on {len(SCENARIOS)} scenarios...")
            print("─" * 40)
            
            evaluator = ScenarioEvaluator(agent_name=agent_name)
            results = await evaluator.run_all_scenarios()
            results_by_agent[agent_name] = results
        
        print(generate_comparison_report(results_by_agent))
    
    asyncio.run(main())
