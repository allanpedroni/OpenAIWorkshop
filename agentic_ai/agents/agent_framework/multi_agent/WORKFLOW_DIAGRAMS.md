# Workflow-Based Reflection Agent - Architecture Diagrams

## 3-Party Communication Flow

```mermaid
graph TD
    User[User] -->|PrimaryAgentRequest| PA[PrimaryAgent Executor]
    PA -->|ReviewRequest| RA[ReviewerAgent Executor]
    RA -->|ReviewResponse approved=false| PA
    RA -->|AgentRunUpdateEvent approved=true| User
    
    style User fill:#e1f5ff
    style PA fill:#fff4e1
    style RA fill:#e8f5e8
```

## Detailed Workflow Execution

```mermaid
sequenceDiagram
    participant User
    participant WorkflowAgent
    participant PrimaryAgent
    participant ReviewerAgent
    
    User->>WorkflowAgent: chat_async("Help with customer 1")
    WorkflowAgent->>PrimaryAgent: PrimaryAgentRequest<br/>(prompt + history)
    
    Note over PrimaryAgent: Generate response<br/>using MCP tools<br/>and conversation history
    
    PrimaryAgent->>ReviewerAgent: ReviewRequest<br/>(prompt + history + response)
    
    Note over ReviewerAgent: Evaluate response quality<br/>Check accuracy, completeness,<br/>professionalism
    
    alt Response Approved
        ReviewerAgent->>ReviewerAgent: AgentRunUpdateEvent
        ReviewerAgent->>WorkflowAgent: Emit to user
        WorkflowAgent->>User: Final response
    else Response Rejected
        ReviewerAgent->>PrimaryAgent: ReviewResponse<br/>(approved=false, feedback)
        
        Note over PrimaryAgent: Incorporate feedback<br/>Regenerate response
        
        PrimaryAgent->>ReviewerAgent: ReviewRequest<br/>(refined response)
        
        Note over ReviewerAgent: Re-evaluate
        
        ReviewerAgent->>ReviewerAgent: AgentRunUpdateEvent
        ReviewerAgent->>WorkflowAgent: Emit to user
        WorkflowAgent->>User: Final response
    end
```

## Message Types

```mermaid
classDiagram
    class PrimaryAgentRequest {
        +str request_id
        +str user_prompt
        +list~ChatMessage~ conversation_history
    }
    
    class ReviewRequest {
        +str request_id
        +str user_prompt
        +list~ChatMessage~ conversation_history
        +list~ChatMessage~ primary_agent_response
    }
    
    class ReviewResponse {
        +str request_id
        +bool approved
        +str feedback
    }
    
    class ReviewDecision {
        +bool approved
        +str feedback
    }
    
    PrimaryAgentRequest --> ReviewRequest : transforms to
    ReviewRequest --> ReviewDecision : evaluates into
    ReviewDecision --> ReviewResponse : converts to
    ReviewResponse --> PrimaryAgentRequest : triggers retry if rejected
```

## Workflow Graph Structure

```mermaid
graph LR
    Start([Start]) --> PA[PrimaryAgent<br/>Executor]
    PA -->|ReviewRequest| RA[ReviewerAgent<br/>Executor]
    RA -->|ReviewResponse<br/>approved=false| PA
    RA -->|AgentRunUpdateEvent<br/>approved=true| End([User])
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style PA fill:#FFE4B5
    style RA fill:#E0BBE4
```

## State Management

```mermaid
stateDiagram-v2
    [*] --> UserInput: User sends prompt
    
    UserInput --> PrimaryGenerate: Create PrimaryAgentRequest<br/>with conversation history
    
    PrimaryGenerate --> ReviewEvaluate: Send ReviewRequest<br/>to ReviewerAgent
    
    ReviewEvaluate --> Approved: Quality check passes
    ReviewEvaluate --> Rejected: Quality check fails
    
    Rejected --> PrimaryRefinement: Send ReviewResponse<br/>with feedback
    
    PrimaryRefinement --> ReviewEvaluate: Send refined ReviewRequest
    
    Approved --> EmitToUser: AgentRunUpdateEvent
    
    EmitToUser --> UpdateHistory: Add to conversation history
    
    UpdateHistory --> [*]: Return response to user
    
    note right of ReviewEvaluate
        Conditional Gate:
        - Accuracy
        - Completeness
        - Professionalism
        - Tool usage
        - Clarity
    end note
    
    note right of PrimaryRefinement
        Incorporate feedback:
        - Add reviewer feedback to context
        - Regenerate response
        - Maintain conversation history
    end note
```

## Conversation History Flow

```mermaid
graph TB
    subgraph "State Store"
        History[Conversation History<br/>User ↔ PrimaryAgent only]
    end
    
    subgraph "Request 1"
        U1[User: Query 1] --> P1[PrimaryAgent]
        P1 --> R1[ReviewerAgent]
        R1 -->|approved| H1[Add to History]
        H1 --> History
    end
    
    subgraph "Request 2 with History"
        History --> P2[PrimaryAgent<br/>receives history]
        U2[User: Query 2] --> P2
        P2 --> R2[ReviewerAgent<br/>receives history]
        R2 -->|approved| H2[Add to History]
        H2 --> History
    end
    
    style History fill:#FFE4E1
    style H1 fill:#90EE90
    style H2 fill:#90EE90
```

## Comparison: Traditional vs Workflow

```mermaid
graph TB
    subgraph "Traditional Reflection Agent"
        T1[Agent.run Step 1:<br/>Primary generates] --> T2[Agent.run Step 2:<br/>Reviewer evaluates]
        T2 --> T3{Approved?}
        T3 -->|No| T4[Agent.run Step 3:<br/>Primary refines]
        T4 --> T2
        T3 -->|Yes| T5[Return to user]
        
        style T1 fill:#FFE4B5
        style T2 fill:#E0BBE4
        style T4 fill:#FFE4B5
    end
    
    subgraph "Workflow Reflection Agent"
        W1[PrimaryAgentExecutor<br/>handles request] --> W2[ReviewerAgentExecutor<br/>evaluates]
        W2 --> W3{Approved?}
        W3 -->|No| W4[PrimaryAgentExecutor<br/>handles feedback]
        W4 --> W2
        W3 -->|Yes| W5[AgentRunUpdateEvent<br/>to user]
        
        style W1 fill:#FFE4B5
        style W2 fill:#E0BBE4
        style W4 fill:#FFE4B5
        style W5 fill:#90EE90
    end
```

## MCP Tool Integration

```mermaid
graph LR
    subgraph "Workflow"
        PA[PrimaryAgent] --> RA[ReviewerAgent]
        RA --> PA
    end
    
    subgraph "MCP Tools"
        T1[get_customer_detail]
        T2[get_billing_summary]
        T3[get_promotions]
        T4[search_knowledge_base]
    end
    
    PA -.->|Uses tools| T1
    PA -.->|Uses tools| T2
    PA -.->|Uses tools| T3
    PA -.->|Uses tools| T4
    
    RA -.->|May use tools<br/>to verify| T1
    
    subgraph "MCP Server"
        MCP[HTTP MCP Server<br/>:5000/mcp]
    end
    
    T1 --> MCP
    T2 --> MCP
    T3 --> MCP
    T4 --> MCP
    
    style PA fill:#FFE4B5
    style RA fill:#E0BBE4
    style MCP fill:#E1F5FF
```

## Error Handling Flow

```mermaid
graph TD
    Start([User Query]) --> Init[Initialize Workflow]
    
    Init --> CheckEnv{Env Config OK?}
    CheckEnv -->|No| Error1[Raise RuntimeError]
    CheckEnv -->|Yes| CreateReq[Create PrimaryAgentRequest]
    
    CreateReq --> PA[PrimaryAgent Process]
    
    PA --> CheckPA{Primary Success?}
    CheckPA -->|Error| Error2[Log error + Raise]
    CheckPA -->|Success| RA[ReviewerAgent Process]
    
    RA --> CheckRA{Review Success?}
    CheckRA -->|Error| Error3[Log error + Raise]
    CheckRA -->|Success| Decision{Approved?}
    
    Decision -->|Yes| Success[Return to User]
    Decision -->|No| CheckRetry{Max Retries?}
    
    CheckRetry -->|Exceeded| Error4[Log warning + Return best attempt]
    CheckRetry -->|Continue| PA
    
    style Error1 fill:#FFB6C1
    style Error2 fill:#FFB6C1
    style Error3 fill:#FFB6C1
    style Error4 fill:#FFE4B5
    style Success fill:#90EE90
```

## Streaming Events Flow

```mermaid
sequenceDiagram
    participant User
    participant Backend
    participant WorkflowAgent
    participant WebSocket
    
    User->>Backend: Send query
    Backend->>WorkflowAgent: chat_async(query)
    
    WorkflowAgent->>WebSocket: orchestrator: "plan"<br/>"Workflow starting..."
    WebSocket->>User: Display plan
    
    WorkflowAgent->>WebSocket: agent_start: "primary_agent"
    WebSocket->>User: Show agent badge
    
    loop Primary Generation
        WorkflowAgent->>WebSocket: agent_token: chunk
        WebSocket->>User: Stream text
    end
    
    WorkflowAgent->>WebSocket: agent_message: complete
    WebSocket->>User: Display message
    
    WorkflowAgent->>WebSocket: orchestrator: "progress"<br/>"Reviewer evaluating..."
    WebSocket->>User: Update progress
    
    WorkflowAgent->>WebSocket: agent_start: "reviewer_agent"
    WebSocket->>User: Show reviewer badge
    
    loop Reviewer Evaluation
        WorkflowAgent->>WebSocket: agent_token: chunk
        WebSocket->>User: Stream text
    end
    
    alt Approved
        WorkflowAgent->>WebSocket: orchestrator: "result"<br/>"Approved!"
        WorkflowAgent->>WebSocket: final_result: response
        WebSocket->>User: Display final response
    else Rejected
        WorkflowAgent->>WebSocket: orchestrator: "progress"<br/>"Refining..."
        Note over WorkflowAgent: Loop back to Primary
    end
```

---

## How to View These Diagrams

These diagrams use Mermaid syntax, which is supported by:

1. **GitHub**: Automatically rendered in Markdown files
2. **VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **Online**: Copy to https://mermaid.live
4. **Documentation sites**: GitBook, Docusaurus, etc.

## Legend

- 🟢 **Green**: Success/approval states
- 🟡 **Yellow**: Processing/agent executors
- 🟣 **Purple**: Review/evaluation
- 🔵 **Blue**: User/external
- 🔴 **Red**: Error states
- ➡️ **Solid arrows**: Direct message flow
- ⤏ **Dashed arrows**: Tool calls/side effects
