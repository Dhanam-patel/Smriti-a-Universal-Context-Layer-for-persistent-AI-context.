# UCL — Technology Specification

## 1. Frontend / Web Application

Use:

```text
Next.js
TypeScript
React
```

Use the current stable Next.js version available when implementation begins, unless the development environment requires a compatible version.

Do not downgrade to an old version without a technical reason.

---

# 2. Rendering

Use standard Next.js architecture.

Prefer:

* Server Components where appropriate
* Client Components only where interactivity requires them
* Server-side handling for sensitive operations

Do not unnecessarily make the entire application client-rendered.

---

# 3. Authentication

Use Google OAuth.

The authentication system must provide:

* Google sign-in
* authenticated session
* user identity
* logout
* protected dashboard routes

Never expose authentication secrets to the browser.

---

# 4. Web Backend

The Next.js application may use:

* Route Handlers
* Server Actions
* server-side service modules

Use the simplest native Next.js approach.

Do not create a separate Node/Express backend unless explicitly requested.

---

# 5. MCP Server

Use:

```text
Python 3.12+
FastAPI
Official MCP Python SDK
Pinecone Python SDK
```

Pin dependency versions in the Python dependency file after selecting compatible stable versions.

Do not use an unrelated MCP implementation.

---

# 6. Vector Database

Use:

```text
Pinecone
```

The Pinecone SDK must be used server-side.

Never expose a Pinecone API key to browser JavaScript.

---

# 7. Control-Plane Database

A small relational database is permitted and expected for:

```text
users
pinecone_connections
mcp_connections
chats
```

The exact provider may be selected during implementation if it is required by the chosen authentication architecture.

However:

* Do not use it as the primary context store.
* Do not duplicate all Pinecone context into it.
* Do not introduce it solely to over-engineer the prototype.

---

# 8. Styling

Use a clean, modern, minimal dashboard.

The interface should prioritize:

* readability
* clear hierarchy
* functional navigation
* responsive layout
* useful empty states
* loading states
* error states

Avoid unnecessary visual complexity.

---

# 9. Environment Variables

Secrets must be environment variables.

Examples:

```text
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET

DATABASE_URL

PINECONE_API_KEY
```

Additional variables may be required by the selected authentication and MCP implementation.

Do not commit secrets.

Do not hard-code API keys.

---

# 10. Production/Development Environments

Support:

```text
development
production
```

Do not assume local-only configuration.

The MCP endpoint must be externally reachable in production.

---

# 11. Deployment

The web application and MCP server must be independently deployable.

Example:

```text
web.example.com
mcp.example.com
```

Exact hosting providers are not fixed by this specification.

Do not introduce a hosting provider dependency into application architecture unnecessarily.

---

# 12. Type Safety

TypeScript:

* strict mode enabled

Python:

* type hints required for public functions
* request/response models should be explicit

Avoid untyped `any` unless technically necessary.

---

# 13. Dependency Policy

Do not install a dependency merely because it is convenient.

Before adding a major dependency:

1. Check whether the functionality already exists in the selected framework.
2. Check whether the dependency is necessary.
3. Prefer maintained official libraries.
4. Keep the dependency footprint small.

---

# 14. Version Policy

Do not invent outdated versions.

When implementation starts:

1. Use the current stable version compatible with the environment.
2. Pin production dependencies.
3. Record major dependency versions in the project documentation.
4. Ensure Next.js, React and authentication dependencies are mutually compatible.
5. Ensure the MCP SDK and FastAPI versions are mutually compatible.

If a specific version is required by the hosting environment, document why.
