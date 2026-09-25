# UCL — Universal Context Layer

## Master Agent Instructions

## 1. Purpose

This directory contains the authoritative product, architecture, technical, data, API, MCP, and development specifications for the Universal Context Layer (UCL) prototype.

The development agent MUST read all files in `.agent/` before making architectural or implementation decisions.

The files are complementary:

* `PRODUCT.md` defines what is being built.
* `ARCHITECTURE.md` defines how the system is structured.
* `TECH_STACK.md` defines the technology choices.
* `DATA_MODEL.md` defines data structures and relationships.
* `API_SPEC.md` defines application APIs.
* `MCP_SPEC.md` defines MCP behavior and protocol.
* `DEVELOPMENT_RULES.md` defines implementation constraints.

If a requirement is not explicitly defined, the development agent MUST NOT silently invent a major architectural decision.

For minor implementation details, choose the simplest implementation compatible with the specifications.

For major architectural ambiguity, stop and request clarification rather than introducing new infrastructure.

---

# 2. Product Definition

UCL is a Universal Context Layer that allows a user to:

1. Authenticate with Google.
2. Connect their own Pinecone vector database/index.
3. Create UCL chats/contexts.
4. View and manage context from the UCL dashboard.
5. Create a user-specific MCP connection.
6. Connect that MCP connection to external AI/agentic applications.
7. Allow those AI applications to read and write context through UCL.
8. Explicitly select a UCL chat/context using the `/UCL/<chat>` convention.

The prototype has only two MCP operations:

* `read_context`
* `write_context`

Do not implement additional MCP tools unless explicitly requested.

---

# 3. Core Architectural Principle

There is exactly ONE hosted UCL MCP service.

There must NOT be one deployed MCP server per user.

The architecture is:

```text
                    UCL MCP Infrastructure
                            |
                  +---------+---------+
                  |                   |
               User A               User B
                  |                   |
          MCP Connection A     MCP Connection B
                  |                   |
             Pinecone A           Pinecone B
```

A user-specific MCP connection identifies and authorizes access to that user's UCL account and Pinecone configuration.

The MCP connection is NOT a separate server deployment.

---

# 4. Two Primary Components

The prototype consists of two independently deployable applications:

## Web Application

Technology:

* Next.js
* TypeScript
* React

Responsibilities:

* Google authentication
* User account
* Pinecone connection
* UCL chat/context management
* Context read/write UI
* MCP connection creation and management
* Documentation

## MCP Server

Technology:

* Python
* FastAPI
* MCP SDK

Responsibilities:

* Expose UCL context through MCP
* Authenticate MCP clients
* Resolve MCP connection to UCL user
* Resolve user's Pinecone configuration
* Read context
* Write context

---

# 5. Vector Database

The prototype uses:

**Pinecone**

Pinecone is the vector database/vector index.

Do not introduce:

* PostgreSQL as context storage
* Qdrant
* Weaviate
* Milvus
* Chroma
* R2
* S3
* Graph databases

unless explicitly requested.

A small relational database may be used as the UCL control-plane database for users, connections, and metadata. It is NOT the source of truth for context.

---

# 6. Source of Truth

For the prototype:

```text
Pinecone
    |
    +-- actual user context
    +-- embeddings
    +-- context metadata
```

The UCL application database stores control-plane information:

```text
User
Pinecone connection
MCP connection
Chat metadata
```

Do not duplicate the entire user's context into the control-plane database.

---

# 7. User Isolation

Every user must be isolated.

User A MUST NOT be able to:

* see User B's Pinecone credentials
* access User B's MCP connection
* read User B's context
* write to User B's context
* access User B's chats

Every request must resolve to an authenticated user before accessing Pinecone.

Never use a global Pinecone credential for all users.

---

# 8. UCL Chat Concept

A UCL user can create multiple logical contexts/chats.

Example:

```text
LLM
Biodegradable
Raw Abroad
UCL Architecture
```

For the prototype, use a Pinecone namespace for each UCL chat.

Example:

```text
Pinecone Index
|
+-- namespace: llm
+-- namespace: biodegradable
+-- namespace: raw-abroad
+-- namespace: ucl-architecture
```

---

# 9. Context Routing

The human-facing routing convention is:

```text
/UCL/<chat>
```

Examples:

```text
/UCL/llm
/UCL/biodegradable
/UCL/raw-abroad
```

The string identifies which UCL context the AI should use.

The MCP server must receive structured data such as:

```json
{
  "chat": "biodegradable",
  "query": "What did we previously discuss about PLA?"
}
```

Do not make the MCP server parse arbitrary natural-language prompts.

The agent/client is responsible for recognizing `/UCL/<chat>` and passing the selected chat to the MCP tool.

---

# 10. MCP Tools

The prototype exposes exactly two tools:

```text
read_context
write_context
```

Do not implement:

```text
delete_context
summarize_context
list_context
create_chat
delete_chat
merge_context
classify_context
```

unless explicitly requested.

---

# 11. Dashboard Operations

The UCL dashboard must provide equivalent context operations.

The dashboard and MCP should use the same underlying context-service logic.

Do not implement two unrelated Pinecone integrations.

Conceptually:

```text
Dashboard
    |
    v
Context Service
    |
    v
Pinecone

MCP
    |
    v
Context Service
    |
    v
Pinecone
```

---

# 12. Implementation Philosophy

Build the smallest working prototype.

Do not:

* over-engineer
* create unnecessary abstractions
* add speculative infrastructure
* create multiple providers
* create microservices unnecessarily
* introduce queues without need
* introduce GraphRAG
* introduce agent orchestration
* introduce automatic memory classification
* introduce enterprise RBAC
* introduce billing
* introduce analytics

The goal is a working end-to-end proof of concept.

---

# 13. Required End-to-End Flow

The completed prototype must support:

```text
Google Login
      |
      v
UCL Account
      |
      v
Connect Pinecone
      |
      v
Validate Pinecone
      |
      v
Create UCL Chat
      |
      v
View Context
      |
      v
Create MCP Connection
      |
      v
Receive MCP endpoint + authentication information
      |
      v
Configure external AI client
      |
      v
AI uses /UCL/<chat>
      |
      v
read_context / write_context
      |
      v
User's Pinecone namespace
```

---

# 14. No Hidden Assumptions

The development agent MUST NOT:

* replace Pinecone with another database
* replace Next.js without permission
* replace FastAPI without permission
* create a separate MCP deployment for every user
* create a separate Pinecone index for every chat
* treat a connection URL as sufficient authentication
* make the user's Pinecone API key public
* expose credentials to the browser
* store plaintext credentials unnecessarily
* search all user contexts when a specific `/UCL/<chat>` context is selected
* mix contexts
* add undocumented MCP tools
* invent undocumented APIs
* introduce additional infrastructure simply because it is familiar

---

# 15. Definition of Done

The prototype is considered complete only when:

1. Google login works.
2. A user can connect their Pinecone configuration.
3. Pinecone connection validation works.
4. User's Pinecone data can be retrieved.
5. UCL chats can be created.
6. Chats map to isolated Pinecone namespaces.
7. Context can be read from the dashboard.
8. Context can be written from the dashboard.
9. A user can create an MCP connection.
10. The MCP endpoint is user-specific.
11. MCP authentication is enforced.
12. `read_context` works.
13. `write_context` works.
14. MCP requests resolve to the correct user.
15. MCP requests resolve to the selected chat.
16. `/UCL/<chat>` routing is documented.
17. User A cannot access User B's context.
18. Dashboard and MCP operate on the same underlying context.
19. No major out-of-scope infrastructure has been introduced.

---

# 16. Agent Working Rule

Before coding:

1. Read every `.agent/*.md` file.
2. Understand the architecture.
3. Inspect the repository.
4. Identify conflicts between existing code and the specification.
5. Do not immediately rewrite existing code.
6. Preserve working code where possible.
7. Implement incrementally.
8. Validate each major milestone.
9. Report architectural deviations before making them.

When uncertain about a major decision, ask instead of assuming.
