# UCL — Development Rules

## 1. General Rule

Build exactly what is specified.

Do not expand the product scope based on assumptions about what UCL might eventually become.

---

# 2. Read Specifications First

Before writing implementation code:

```text
.agent/AGENTS.md
.agent/PRODUCT.md
.agent/ARCHITECTURE.md
.agent/TECH_STACK.md
.agent/DATA_MODEL.md
.agent/API_SPEC.md
.agent/MCP_SPEC.md
.agent/DEVELOPMENT_RULES.md
```

must be read.

---

# 3. Existing Repository

Before modifying the repository:

1. Inspect the existing files.
2. Identify the current framework.
3. Identify existing dependencies.
4. Identify existing configuration.
5. Identify existing authentication.
6. Identify existing deployment configuration.

Do not blindly replace an existing working application.

---

# 4. Code Organization

Recommended repository:

```text
ucl/
│
├── .agent/
│   ├── AGENTS.md
│   ├── PRODUCT.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── DATA_MODEL.md
│   ├── API_SPEC.md
│   ├── MCP_SPEC.md
│   └── DEVELOPMENT_RULES.md
│
├── apps/
│   ├── web/
│   └── mcp/
│
├── packages/
│   └── shared/
│
├── docs/
│
├── README.md
├── .gitignore
└── package configuration
```

The `packages/shared` directory is optional.

Do not force code sharing between Python and TypeScript merely for theoretical reuse.

---

# 5. Web Structure

Recommended:

```text
apps/web/
│
├── app/
│   ├── (auth)/
│   ├── dashboard/
│   ├── context/
│   ├── mcp/
│   ├── docs/
│   ├── settings/
│   └── api/
│
├── components/
│   ├── ui/
│   ├── dashboard/
│   ├── context/
│   └── mcp/
│
├── lib/
│   ├── auth/
│   ├── pinecone/
│   ├── context/
│   ├── mcp/
│   └── db/
│
├── types/
│
└── tests/
```

The exact Next.js route structure may be adjusted to the selected authentication framework.

---

# 6. MCP Structure

Recommended:

```text
apps/mcp/
│
├── app/
│   ├── main.py
│   ├── server.py
│   ├── auth.py
│   ├── config.py
│   │
│   ├── tools/
│   │   ├── read_context.py
│   │   └── write_context.py
│   │
│   ├── services/
│   │   ├── context_service.py
│   │   ├── pinecone_service.py
│   │   └── connection_service.py
│   │
│   ├── models/
│   │   └── ...
│   │
│   └── utils/
│
├── tests/
│
├── requirements.txt / pyproject.toml
└── README.md
```

---

# 7. Naming

Use clear names.

Prefer:

```text
read_context
write_context
pinecone_service
mcp_connection
```

Avoid:

```text
handler2
utils_final
temp_service
new_mcp
memory_manager_final
```

---

# 8. Environment Variables

Never commit:

```text
API keys
OAuth secrets
database passwords
MCP secrets
```

Use environment variables or secure secret storage.

---

# 9. Logging

Logs must never contain:

* Pinecone API keys
* OAuth client secrets
* MCP authentication secrets
* raw authorization headers

Development logs may contain safe IDs and operation names.

---

# 10. Error Handling

Every external dependency must have controlled error handling.

External systems include:

* Google authentication
* Pinecone
* database
* MCP client

Do not allow raw stack traces to reach users.

---

# 11. Loading States

The dashboard must handle:

```text
loading
success
empty
error
```

Examples:

```text
Connecting to Pinecone...
```

```text
No contexts created yet.
```

```text
Unable to connect to Pinecone.
```

---

# 12. Security

Security requirements are mandatory.

Never:

* expose credentials to frontend code
* trust client-provided user IDs
* trust client-provided ownership
* allow arbitrary Pinecone index selection after authentication
* expose another user's data
* put secrets in URLs
* log secrets

---

# 13. Input Validation

Validate:

* chat names
* slugs
* MCP connection inputs
* Pinecone configuration
* context content
* search queries

Do not assume client-side validation is sufficient.

Server-side validation is required.

---

# 14. Testing

At minimum, test:

### Authentication

* login
* logout
* protected route

### Pinecone

* valid connection
* invalid credentials
* unavailable index

### Context

* create chat
* read context
* write context
* user isolation

### MCP

* valid authentication
* invalid authentication
* revoked connection
* read_context
* write_context
* chat isolation
* user isolation

---

# 15. Critical Security Test

Create:

```text
User A
User B
```

User A must never be able to:

```text
read User B's context
write User B's context
access User B's MCP connection
access User B's Pinecone credentials
```

This test is mandatory.

---

# 16. Context Isolation Test

Create:

```text
LLM
Biodegradable
```

Store different information in each.

A request for:

```text
/UCL/llm
```

must not return information from:

```text
biodegradable
```

---

# 17. MCP Test

The final integration test should demonstrate:

```text
External AI
     ↓
UCL MCP
     ↓
read_context
     ↓
LLM namespace
     ↓
Pinecone
```

Then:

```text
External AI
     ↓
UCL MCP
     ↓
write_context
     ↓
LLM namespace
     ↓
Pinecone
```

The dashboard must subsequently display the written information.

---

# 18. No Premature Optimization

Do not optimize:

* embeddings
* ranking
* chunking
* caching
* retrieval algorithms

until the basic system works.

---

# 19. No Unapproved Architecture Changes

Before introducing:

* Redis
* queues
* workers
* Kafka
* Graph databases
* object storage
* additional vector databases
* microservices
* Kubernetes
* complex caching

stop and request approval.

---

# 20. Development Sequence

Build in this order:

### Phase 1

Project setup.

### Phase 2

Google authentication.

### Phase 3

Control-plane database.

### Phase 4

Pinecone connection.

### Phase 5

Pinecone connection validation.

### Phase 6

Chat creation.

### Phase 7

Dashboard context read/write.

### Phase 8

MCP connection creation.

### Phase 9

MCP authentication.

### Phase 10

`read_context`.

### Phase 11

`write_context`.

### Phase 12

`/UCL/<chat>` documentation and agent instructions.

### Phase 13

End-to-end integration testing.

---

# 21. Final Principle

The prototype should remain understandable.

A developer should be able to explain the system as:

```text
User
 ↓
Google Login
 ↓
Connect Pinecone
 ↓
Create UCL Context
 ↓
Create MCP Connection
 ↓
Connect AI
 ↓
/UCL/<context>
 ↓
read_context / write_context
 ↓
Pinecone
```

If the implementation becomes substantially more complicated than this without a documented requirement, reconsider the architecture.
