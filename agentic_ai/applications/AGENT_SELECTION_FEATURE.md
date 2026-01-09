# Agent Selection Feature

## Overview

This feature adds UI-based agent selection to the Magentic AI Assistant, allowing users to dynamically switch between different agent implementations without manually editing the `.env` file.

## Changes Made

### Backend Changes (`backend.py`)

1. **Agent Module Management**
   - Replaced static agent loading with dynamic loading system
   - Added `AVAILABLE_AGENTS` list containing all selectable agent modules:
     - `agents.agent_framework.single_agent`
     - `agents.agent_framework.multi_agent.handoff_multi_domain_agent`
     - `agents.agent_framework.multi_agent.magentic_group`
     - `agents.agent_framework.multi_agent.reflection_agent`
   - Created `load_agent_class()` function for dynamic agent module loading
   - Added `CURRENT_AGENT_MODULE` global variable to track active agent

2. **New API Endpoints**
   - **GET `/agents`**: Returns list of available agents with their display names and descriptions
   - **POST `/agents/set`**: Changes the active agent module at runtime

### Frontend Changes (`react-frontend/src/App.js`)

1. **UI Components**
   - Added agent selector dropdown in the AppBar
   - Added Snackbar component for user notifications
   - Imported Material-UI components: `Select`, `MenuItem`, `FormControl`, `InputLabel`, `Alert`, `Snackbar`

2. **State Management**
   - Added `availableAgents` state to store list of available agents
   - Added `currentAgent` state to track the currently active agent
   - Added `snackbar` state for user notifications

3. **Functionality**
   - `handleAgentChange()`: Handler for agent selection changes
   - Fetches available agents on component mount
   - Automatically starts new session when agent is changed
   - Shows success/error notifications for agent switching

## Usage

1. **Start the Backend**
   ```bash
   cd agentic_ai/applications
   python backend.py
   ```

2. **Start the React Frontend**
   ```bash
   cd agentic_ai/applications/react-frontend
   npm run dev
   ```

3. **Using Agent Selection**
   - Look for the "Active Agent" dropdown in the top navigation bar
   - Click to see all available agent implementations
   - Select an agent to switch (automatically starts a new session)
   - Receive confirmation notification

## Features

### Available Agents

1. **Single Agent**
   - Simple single-agent chat without orchestration
   - Good for basic conversations

2. **Handoff Multi Domain Agent**
   - Multi-agent system with domain-specific specialists
   - Automatic handoffs between specialists (Billing, Products, Security)

3. **Magentic Group**
   - MagenticOne-style orchestrator with specialist agents
   - Task planning and delegation

4. **Reflection Agent**
   - Agent with built-in reflection and self-critique
   - Iterative improvement of responses


### Benefits

- ✅ No need to edit `.env` file manually
- ✅ Switch agents on-the-fly without restarting backend
- ✅ Visual feedback for agent changes
- ✅ Each agent shows descriptive information
- ✅ Automatic session reset on agent change
- ✅ Type-safe agent loading with error handling

## Technical Details

### Backend Architecture

The backend now supports hot-swapping of agent modules:

```python
# Load agent dynamically
Agent = load_agent_class(CURRENT_AGENT_MODULE)

# Switch agent at runtime
CURRENT_AGENT_MODULE = new_module_path
Agent = load_agent_class(CURRENT_AGENT_MODULE)
```

### Frontend Architecture

The frontend uses Material-UI Select component with custom styling for the AppBar:

```javascript
<Select
  value={currentAgent}
  onChange={handleAgentChange}
  // White-themed for dark AppBar
/>
```

### API Contract

**GET `/agents`**
```json
{
  "agents": [
    {
      "module_path": "agents.agent_framework.single_agent",
      "display_name": "Single Agent",
      "description": "Simple single-agent chat without orchestration"
    }
  ],
  "current_agent": "agents.agent_framework.single_agent"
}
```

**POST `/agents/set`**
```json
// Request
{
  "module_path": "agents.agent_framework.multi_agent.reflection_agent"
}

// Response
{
  "status": "success",
  "message": "Active agent changed to ...",
  "current_agent": "agents.agent_framework.multi_agent.reflection_agent"
}
```

## Future Enhancements

Potential improvements:
- [ ] Persist agent selection in localStorage
- [ ] Add agent-specific configuration UI
- [ ] Show agent capabilities/features in selection UI
- [ ] Allow custom agent module paths
- [ ] Add agent performance metrics
- [ ] Support agent-specific parameters

## Troubleshooting

### Agent fails to load
- Check that the agent module exists at the specified path
- Verify the agent class exports an `Agent` class
- Check backend console for detailed error messages

### Dropdown not showing agents
- Verify backend is running and accessible
- Check browser console for API errors
- Ensure CORS is properly configured

### Session not resetting
- Check WebSocket connection status
- Verify backend reset_session endpoint is working
- Check browser console for errors

## Notes

- Agent changes take effect immediately
- All active sessions are preserved (multi-session support)
- WebSocket reconnection is automatic
- Auth tokens (if configured) are maintained across agent changes
