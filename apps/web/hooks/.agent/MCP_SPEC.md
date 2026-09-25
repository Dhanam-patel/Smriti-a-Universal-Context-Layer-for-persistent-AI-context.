# UCL — MCP Server Specification

## 1. Purpose

The UCL MCP server provides AI applications with controlled access to a user's UCL context.

The MCP server is a shared multi-tenant service.

---

# 2. Deployment Model

There is exactly ONE MCP service.

Example:

```text
https://mcp.example.com
```

Do not deploy one MCP server per user.

---

# 3. User-Specific MCP Connection

Each user can create an MCP connection.

Example:

```text
https://mcp.example.com/mcp/cn_8f72k19d
```

The connection ID must be:

* random
* opaque
* non-sequential
* non-guessable

The URL identifies the MCP connection.

It does not independently constitute authorization.

---

# 4. Authentication

Every MCP request must be authenticated.

The implementation should use the authentication mechanism supported by the selected MCP SDK and deployment architecture.

The architecture must support:

```text
MCP client
    ↓
authentication
    ↓
MCP connection
    ↓
UCL user
```

Do not rely solely on the URL.

---

# 5. User Resolution

Every authenticated MCP request must resolve:

```text
MCP credential
      ↓
MCP connection
      ↓
UCL user
      ↓
Pinecone connection
```

The MCP request must never allow the caller to choose another user's credentials.

---

# 6. Tool Count

The prototype exposes exactly two tools.

```text
read_context
write_context
```

---

# 7. read_context

Purpose:

Retrieve semantically relevant context from a selected UCL chat.

Conceptual schema:

```json
{
  "chat": "biodegradable",
  "query": "What did we previously discuss about PLA?"
}
```

Required fields:

```text
chat
query
```

Behavior:

1. Authenticate MCP request.
2. Resolve UCL user.
3. Verify requested chat belongs to user.
4. Resolve user's Pinecone connection.
5. Resolve chat namespace.
6. Generate query embedding.
7. Search Pinecone.
8. Return relevant context.

---

# 8. write_context

Purpose:

Persist new context into a selected UCL chat.

Conceptual schema:

```json
{
  "chat": "biodegradable",
  "content": "PLA has limitations around heat resistance."
}
```

Required fields:

```text
chat
content
```

Behavior:

1. Authenticate MCP request.
2. Resolve UCL user.
3. Verify requested chat belongs to user.
4. Resolve user's Pinecone connection.
5. Generate embedding.
6. Upsert into selected namespace.
7. Return success.

---

# 9. `/UCL/<chat>` Convention

The human-facing UCL routing syntax is:

```text
/UCL/<chat>
```

Examples:

```text
/UCL/llm
/UCL/biodegradable
/UCL/raw-abroad
```

This is an instruction convention for AI clients.

The MCP server does not need to parse the user's entire natural-language prompt.

The AI client should translate:

```text
/UCL/biodegradable
```

into:

```json
{
  "chat": "biodegradable"
}
```

when calling the MCP tool.

---

# 10. Example Read Flow

User sends:

```text
/UCL/llm

What did we decide about the retrieval architecture?
```

AI client:

```text
Detect UCL context = llm
        ↓
call read_context
        ↓
chat = llm
query = retrieval architecture
```

MCP:

```text
Authenticate
      ↓
Resolve user
      ↓
Resolve llm chat
      ↓
Pinecone namespace = llm
      ↓
Semantic search
      ↓
Return context
```

---

# 11. Example Write Flow

User sends:

```text
/UCL/llm

Remember that Pinecone is the vector database for the prototype.
```

AI client:

```text
chat = llm
content = Pinecone is the vector database for the prototype.
```

MCP:

```text
write_context
      ↓
namespace = llm
      ↓
embedding
      ↓
Pinecone upsert
```

---

# 12. MCP Response

Responses should contain only the information required by the AI client.

Do not expose:

* Pinecone API keys
* UCL internal credentials
* database connection strings
* internal user IDs unless required
* internal implementation details

---

# 13. MCP Errors

Use clear tool errors.

Examples:

```text
AUTHENTICATION_REQUIRED
MCP_CONNECTION_NOT_FOUND
MCP_CONNECTION_REVOKED
CHAT_NOT_FOUND
CHAT_ACCESS_DENIED
PINECONE_NOT_CONNECTED
PINECONE_OPERATION_FAILED
```

Do not leak secrets in errors.

---

# 14. Tool Restrictions

The MCP server must NOT expose arbitrary Pinecone operations.

The AI must not be able to:

* execute arbitrary Pinecone API calls
* select arbitrary indexes
* select arbitrary users
* retrieve credentials
* delete entire indexes
* modify infrastructure

The MCP layer exposes only the UCL context abstraction.

---

# 15. Future MCP Tools

Possible future tools include:

```text
list_contexts
delete_context
create_context
get_context
```

These are NOT part of the prototype.
