# UCL — System Architecture

## 1. High-Level Architecture

```text
                         ┌─────────────────────┐
                         │      UCL Web        │
                         │      Next.js        │
                         └──────────┬──────────┘
                                    │
                                    │
                         ┌──────────▼──────────┐
                         │   UCL Application   │
                         │    / Control Plane  │
                         └──────────┬──────────┘
                                    │
                                    │
                         ┌──────────▼──────────┐
                         │     Context         │
                         │      Service        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                              ┌───────────┐
                              │ Pinecone  │
                              └───────────┘
                                    ▲
                                    │
                         ┌──────────┴──────────┐
                         │    UCL MCP Server   │
                         │    FastAPI/Python   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                              AI / MCP Client
```

---

# 2. Applications

The prototype has two separately deployable applications.

## Application A

```text
apps/web
```

Next.js application.

## Application B

```text
apps/mcp
```

Python FastAPI MCP server.

---

# 3. Shared Context Service

The dashboard and MCP server must perform context operations through the same conceptual service.

Required operations:

```text
read_context
write_context
```

The exact code-sharing mechanism can differ between TypeScript and Python.

The important requirement is behavioral consistency.

---

# 4. Control Plane

The UCL control plane stores:

```text
Users
Pinecone Connections
MCP Connections
Chats
```

It does not store the primary context corpus.

---

# 5. Data Plane

The prototype data plane is:

```text
Pinecone
```

The user's context is stored there.

---

# 6. Multi-Tenant Model

One UCL deployment serves many users.

```text
UCL
│
├── User A
│   ├── Pinecone connection
│   └── MCP connection
│
├── User B
│   ├── Pinecone connection
│   └── MCP connection
│
└── User C
    ├── Pinecone connection
    └── MCP connection
```

---

# 7. MCP Architecture

There is exactly one hosted MCP service.

Example base endpoint:

```text
https://mcp.example.com
```

A user-specific connection may be represented by:

```text
https://mcp.example.com/mcp/<opaque-connection-id>
```

The opaque connection ID is not authentication by itself.

Authentication must also be enforced.

---

# 8. MCP Request Resolution

Every request follows:

```text
MCP request
    ↓
Authenticate caller
    ↓
Resolve MCP connection
    ↓
Resolve UCL user
    ↓
Load user's Pinecone configuration
    ↓
Resolve requested chat
    ↓
Execute read/write operation
    ↓
Return result
```

---

# 9. Chat Isolation

Each UCL chat maps to a Pinecone namespace.

Example:

```text
Pinecone index
│
├── namespace: llm
├── namespace: biodegradable
└── namespace: raw-abroad
```

A request targeting:

```text
/UCL/llm
```

must never retrieve from:

```text
biodegradable
raw-abroad
```

unless explicitly requested in a future feature.

---

# 10. Connection Isolation

Each MCP connection belongs to exactly one UCL user.

Conceptually:

```text
MCP connection
      ↓
UCL user
      ↓
Pinecone connection
      ↓
Pinecone index
```

No cross-user access is allowed.

---

# 11. Dashboard Flow

```text
Google Login
     ↓
Authenticated session
     ↓
Pinecone configuration
     ↓
Connection validation
     ↓
User dashboard
     ↓
Create/select chat
     ↓
Read/write context
```

---

# 12. MCP Flow

```text
External AI
     ↓
MCP connection
     ↓
Authentication
     ↓
User resolution
     ↓
Chat resolution
     ↓
read_context / write_context
     ↓
Pinecone
```

---

# 13. Context Flow

## Read

```text
User query
     ↓
Embedding generation
     ↓
Pinecone semantic search
     ↓
Selected namespace
     ↓
Relevant vectors
     ↓
Metadata/content
     ↓
Response
```

## Write

```text
Content
     ↓
Embedding generation
     ↓
Pinecone upsert
     ↓
Selected namespace
```

---

# 14. Important Architecture Constraint

Pinecone is a vector database.

Do not treat it like a conventional SQL database.

The system should distinguish:

```text
Vector
Embedding
Metadata
Namespace
Index
```

from:

```text
User
Chat
MCP Connection
```

The latter are application/control-plane entities.

---

# 15. Future Architecture

Future provider abstraction may support:

```text
Pinecone
Qdrant
Weaviate
etc.
```

But this is explicitly OUT OF SCOPE for the prototype.

The current implementation should use Pinecone directly.
