# UCL — Product Specification

## 1. Product Name

Universal Context Layer

Short name:

UCL

---

# 2. Product Purpose

UCL is a persistent context layer that allows users to connect their own vector database infrastructure and expose selected context to AI/agentic applications through MCP.

UCL provides two primary interfaces:

1. Human interface — UCL Web Dashboard
2. AI interface — UCL MCP Server

Both interfaces operate on the same underlying user context.

---

# 3. Prototype Goal

The prototype exists to prove:

> A user can connect their Pinecone infrastructure to UCL, create isolated UCL contexts, expose those contexts through a user-specific MCP connection, and allow an external AI agent to read and write those contexts.

---

# 4. User Journey

## Step 1 — Authentication

User opens UCL.

User selects:

```text
Continue with Google
```

The user becomes an authenticated UCL user.

---

## Step 2 — Connect Pinecone

The user is asked to connect their Pinecone account/configuration.

The user provides the required Pinecone configuration.

UCL validates the connection.

The dashboard must clearly show:

```text
Pinecone
Connected
```

---

# 5. Step 3 — Create Context

The user creates a UCL chat/context.

Examples:

```text
LLM
Biodegradable
Raw Abroad
Research
```

Every context receives:

* internal ID
* display name
* slug
* creation timestamp

The slug is used for `/UCL/<chat>` routing.

---

# 6. Step 4 — Dashboard Context

The user can open a chat and see its context.

The dashboard must support:

* reading context
* writing context

The prototype does not need advanced editing functionality unless explicitly implemented as part of the basic write operation.

---

# 7. Step 5 — Create MCP Connection

The user opens the MCP section.

The user selects:

```text
Create MCP Connection
```

UCL creates a connection associated with the authenticated user.

The dashboard displays:

* MCP endpoint
* authentication information
* connection status
* available tools

The user can copy the information into an MCP-compatible AI application.

---

# 8. Step 6 — External AI

The external AI application connects to UCL.

The AI can access:

```text
read_context
write_context
```

---

# 9. Step 7 — Context Selection

The user can specify:

```text
/UCL/llm
```

or:

```text
/UCL/biodegradable
```

This tells the agent which UCL context to access.

The selected context must be respected.

---

# 10. Example

User creates:

```text
Biodegradable
```

UCL generates:

```text
/UCL/biodegradable
```

User sends:

```text
/UCL/biodegradable

What have we previously discussed about PLA?
```

The agent uses:

```text
read_context
```

with:

```text
chat = biodegradable
```

The UCL MCP server retrieves information only from the `biodegradable` context.

---

# 11. Writing Example

User:

```text
/UCL/biodegradable

Remember that PLA has limitations around heat resistance.
```

The agent uses:

```text
write_context
```

The information is written to the `biodegradable` context.

The same information becomes visible from the UCL dashboard.

---

# 12. Prototype UI

Required navigation:

```text
Dashboard
Context
MCP
Docs
Settings
```

Authentication state and user information should also be accessible.

---

# 13. Dashboard

The dashboard should show:

* connection status
* number of contexts
* recent contexts
* basic context activity if easily available

Do not create elaborate analytics.

---

# 14. Context Page

The context page must provide:

* context list
* context selection
* context search/retrieval
* context write functionality

---

# 15. MCP Page

The MCP page must provide:

* connection status
* MCP endpoint
* authentication information
* copy controls
* available tools
* basic connection instructions

---

# 16. Documentation Page

The documentation must explain:

* What UCL is
* Connecting Pinecone
* Creating a context
* Creating MCP connection
* Connecting an MCP client
* `/UCL/<chat>` convention
* `read_context`
* `write_context`
* examples

---

# 17. Product Boundaries

The prototype is NOT:

* a general-purpose database management tool
* a replacement for Pinecone
* a full AI assistant
* a ChatGPT clone
* a multi-agent platform
* an MCP marketplace
* an MCP aggregation platform
* an enterprise knowledge-management platform

Those may become future capabilities.

---

# 18. Core Product Principle

UCL does not replace the user's infrastructure.

UCL provides the management and context-access layer around it.

For the prototype:

```text
User infrastructure
        +
UCL management layer
        +
MCP access layer
```
