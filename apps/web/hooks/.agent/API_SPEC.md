# UCL — Web API Specification

## 1. Purpose

This document defines the backend interface for the UCL web application.

The API must enforce authentication and user ownership.

---

# 2. Authentication

All protected API routes require an authenticated UCL session.

Unauthenticated requests must receive an appropriate authentication error.

---

# 3. Pinecone Connection

## Create/Connect

Conceptual endpoint:

```http
POST /api/pinecone/connect
```

Request:

```json
{
  "apiKey": "...",
  "indexName": "...",
  "host": "..."
}
```

The exact required fields depend on the selected Pinecone connection mechanism.

Behavior:

1. Authenticate user.
2. Validate Pinecone credentials.
3. Validate index access.
4. Store encrypted configuration.
5. Return safe connection status.

Never return the API key.

---

# 4. Pinecone Connection Status

```http
GET /api/pinecone/status
```

Returns:

```json
{
  "connected": true,
  "index": "example-index"
}
```

Never return credentials.

---

# 5. Chats

## List chats

```http
GET /api/chats
```

Returns only the authenticated user's chats.

---

## Create chat

```http
POST /api/chats
```

Request:

```json
{
  "name": "Biodegradable"
}
```

The server generates:

```text
id
slug
namespace
```

---

## Get chat

```http
GET /api/chats/:chatId
```

The user must own the chat.

---

# 6. Read Context

Conceptual endpoint:

```http
POST /api/chats/:chatId/context/search
```

Request:

```json
{
  "query": "What did we discuss about PLA?"
}
```

Behavior:

1. Authenticate user.
2. Verify chat ownership.
3. Resolve user's Pinecone connection.
4. Resolve chat namespace.
5. Generate query embedding.
6. Search Pinecone.
7. Return relevant context.

---

# 7. Write Context

Conceptual endpoint:

```http
POST /api/chats/:chatId/context
```

Request:

```json
{
  "content": "PLA has limitations around heat resistance."
}
```

Behavior:

1. Authenticate user.
2. Verify chat ownership.
3. Resolve Pinecone connection.
4. Generate embedding.
5. Upsert into correct namespace.
6. Return safe result.

---

# 8. MCP Connection

## Create

```http
POST /api/mcp/connections
```

Creates a user-specific MCP connection.

The connection must be associated with the authenticated user.

---

# 9. List MCP Connections

```http
GET /api/mcp/connections
```

Only return the authenticated user's connections.

Do not return secret credentials.

---

# 10. Revoke MCP Connection

The dashboard may eventually support:

```http
DELETE /api/mcp/connections/:id
```

If implemented, revocation must immediately prevent future MCP authentication using that credential.

---

# 11. API Security

All APIs must enforce:

```text
authentication
+
authorization
+
user ownership
```

Do not trust:

```text
user_id
chat_id
connection_id
```

supplied by the browser without validating ownership server-side.

---

# 12. Error Format

Use consistent structured errors.

Example:

```json
{
  "error": {
    "code": "PINECONE_CONNECTION_FAILED",
    "message": "Unable to connect to the configured Pinecone index."
  }
}
```

Do not expose:

* stack traces
* API keys
* internal credentials
* sensitive infrastructure details

in production responses.
