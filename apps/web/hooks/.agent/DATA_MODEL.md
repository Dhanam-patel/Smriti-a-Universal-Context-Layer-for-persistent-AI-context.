# UCL — Data Model

## 1. Overview

The prototype has two categories of data:

### Control-plane data

Stored in the UCL application database:

* users
* Pinecone connections
* MCP connections
* chats

### Context data

Stored in Pinecone:

* embeddings
* context content
* context metadata

---

# 2. User

Conceptual model:

```text
User
-----
id
google_id
email
name
avatar_url
created_at
updated_at
```

The exact authentication-provider fields may differ according to the selected authentication implementation.

---

# 3. Pinecone Connection

Conceptual model:

```text
PineconeConnection
------------------
id
user_id
index_name
host
namespace_prefix (optional)
encrypted_api_key
created_at
updated_at
status
```

Only the fields actually required by Pinecone should be stored.

Do not store unnecessary credentials.

---

# 4. MCP Connection

Conceptual model:

```text
MCPConnection
-------------
id
user_id
connection_id
credential_hash / secure credential representation
status
created_at
last_used_at
```

The `connection_id` should be opaque and randomly generated.

Do not use sequential user IDs as public MCP connection identifiers.

---

# 5. Chat

Conceptual model:

```text
Chat
----
id
user_id
name
slug
pinecone_namespace
created_at
updated_at
```

Example:

```text
name:
Biodegradable

slug:
biodegradable

pinecone_namespace:
biodegradable
```

The implementation may use an internal generated namespace if required.

---

# 6. User Relationships

```text
User
 |
 +-- PineconeConnection
 |
 +-- MCPConnection
 |
 +-- Chat
```

All three must belong to the authenticated user.

---

# 7. Pinecone Context Record

Conceptual record:

```json
{
  "id": "ctx_123",
  "values": [0.123, 0.456],
  "metadata": {
    "content": "PLA has limitations around heat resistance.",
    "title": "PLA limitation",
    "source": "mcp",
    "created_at": "2026-09-25T10:00:00Z",
    "updated_at": "2026-09-25T10:00:00Z"
  }
}
```

The exact embedding dimensions depend on the selected embedding model.

Do not hard-code an incompatible dimension.

---

# 8. Required Context Metadata

At minimum, context records should preserve:

```text
content
source
created_at
updated_at
```

Optional useful fields:

```text
title
context_id
```

Do not unnecessarily create a complex metadata schema.

---

# 9. Namespace Rule

Each UCL chat maps to one Pinecone namespace.

Example:

```text
chat slug: llm
namespace: llm
```

Example:

```text
chat slug: biodegradable
namespace: biodegradable
```

---

# 10. Cross-User Rule

A Pinecone namespace must only be accessed through the authenticated user's Pinecone connection.

Never allow the client to arbitrarily specify another user's index or credentials.

---

# 11. Credential Storage

Pinecone API credentials are sensitive.

They must not be:

* returned in API responses
* exposed to browser JavaScript after initial submission
* logged
* stored in plaintext when secure encryption is available

Use encryption at rest for stored user-provided credentials.

---

# 12. Chat Deletion

Deletion behavior is NOT part of the initial MCP tool set.

If implemented through the dashboard later, the implementation must explicitly define whether deleting a chat also deletes its Pinecone namespace/data.

Do not guess this behavior.
