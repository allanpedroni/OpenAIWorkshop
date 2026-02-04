![alt text](docs/media/image-1.png)
# Microsoft AI Agentic Workshop Repository  
  
Welcome to the official repository for the Microsoft AI Agentic Workshop! This repository provides all the resources, code, and documentation you need to explore, prototype, and compare various agent-based AI solutions using Microsoft's leading AI technologies.  
  
---  
  
## Quick Links  
  
- [Business Scenario and Agent Design](./SCENARIO.md)  
- [Getting Started (Setup Instructions)](./SETUP.md)  
- [System Architecture Overview](./ARCHITECTURE.md)  
- [Data Sets](./DATA.md)  
- [APIM + MCP Security (Optional)](./mcp/MULTI_TENANT_MCP_SECURITY.md)  
- [Code of Conduct](./CODE_OF_CONDUCT.md)  
- [Security Guidelines](./SECURITY.md)  
- [Support](./SUPPORT.md)  
- [License](./LICENSE)  
  
---  
  
## What You Can Do With This Repo  
  
- **Design and prototype AI agent solutions** for real-world business scenarios
- **Explore single-agent and multi-agent architectures** with different orchestration patterns
- **Build with Microsoft Agent Framework** - advanced multi-agent orchestration, handoffs, and checkpointing
- **Build end-to-end agentic AI systems** - Complete architecture from backend database, MCP tools server, agent orchestration, application backend, to React/Streamlit frontend
- **Deploy to Azure with enterprise security** - VNet, private endpoints, managed identity, and CI/CD automation
  
---  
  
## Key Features  

- **[Microsoft Agent Framework](https://github.com/microsoft/agent-framework) Integration** - Single-agent, multi-agent Magentic orchestration, and handoff-based domain routing with MCP tools. [Pattern guide →](agentic_ai/agents/agent_framework/README.md)
- **[Workflow Orchestration](agentic_ai/workflow/)** - Hybrid Workflow + Durable Task architecture with fan-out/fan-in topology, human-in-the-loop, and real-time observability. [Fraud Detection Demo →](agentic_ai/workflow/fraud_detection_durable/)
- **Advanced UI Options** - React frontend with interactive workflow visualization and step-by-step tool call details
- **[MCP Server Integration](mcp/)** - Model Context Protocol for enhanced agent tool capabilities with advanced features: authentication, RBAC, and APIM integration
- **[Emerging Agentic Scenarios](agentic_ai/scenarios/)** - Long-running workflows, progress updates, and durable agent patterns
- **Agent State & History Persistence** - In-memory or CosmosDB backend for conversation history and agent state
- **[Enterprise-Ready Reference Architecture](infra/README.md)** - Production-grade deployment with VNet integration, private endpoints, managed identity, Terraform/Bicep IaC, and GitHub Actions CI/CD  
  
---  
  
## Getting Started  
  
1. Review the [Setup Instructions](./SETUP.md) for environment prerequisites and step-by-step installation.  
2. Explore the [Business Scenario and Agent Design](./SCENARIO.md) to understand the workshop challenge.  
3. Check out the **[Agent Framework Implementation Patterns](agentic_ai/agents/agent_framework/README.md)** to choose the right multi-agent approach (single-agent, Magentic orchestration, or handoff pattern).
4. Try the **[Durable Fraud Detection Workflow](agentic_ai/workflow/fraud_detection_durable/)** to see hybrid Workflow + Durable Task orchestration with human-in-the-loop.
5. Dive into [System Architecture](./ARCHITECTURE.md) before building and customizing your agent solutions.  
6. Utilize the [Support Guide](./SUPPORT.md) for troubleshooting and assistance.  

---

## Deploy to Azure

For enterprise-ready deployment with VNet integration, private endpoints, managed identity, and CI/CD automation, see the **[Deployment Guide](./infra/README.md)**.

| Deployment Method | Description | Guide |
|-------------------|-------------|-------|
| **🚀 Azure Developer CLI** | Single-command quick start | [azd Quick Start](./infra/README.md#azure-developer-cli-azd) |
| **🔧 Manual Deployment** | PowerShell with Terraform/Bicep | [Manual Steps](./infra/README.md#manual-deployment-powershell) |
| **🔒 Enterprise Security** | VNet, Private Endpoints, Managed Identity | [Security Profiles](./infra/README.md#security-profiles) |
| **🚀 CI/CD Automation** | GitHub Actions with OIDC | [GitHub Actions Setup](./infra/GITHUB_ACTIONS_SETUP.md) |
  
---  
  
## Contributing  
  
Please review our [Code of Conduct](./CODE_OF_CONDUCT.md) and [Security Guidelines](./SECURITY.md) before contributing.  
  
---  
  
## License  
  
This project is licensed under the terms described in the [LICENSE](./LICENSE) file.  
  
