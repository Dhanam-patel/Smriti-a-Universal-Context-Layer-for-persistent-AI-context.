# UCL MCP Server

This is the Python FastAPI server that exposes the Model Context Protocol (MCP) to AI clients.
It allows authenticated AI clients to read and write context to a user's Pinecone vector database.

## Technologies

- Python 3.12+
- FastAPI
- MCP Python SDK (Streamable HTTP transport)
- OAuth 2.1 resource-server authentication with Supabase JWT/JWKS validation
- Pinecone Python SDK

- Supabase SDK (for control-plane DB access)

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:

   ```bash
   pip install -r requirements.txt -c constraints.txt
   ```

   `constraints.txt` pins the exact versions the tests were run against; drop `-c` to take the latest compatible releases.

3. Configure environment variables in `.env`:
   ```
   SUPABASE_URL=...
   SUPABASE_SERVICE_ROLE_KEY=...
   # Canonical public server endpoint URL; this is the OAuth resource/audience.
   MCP_RESOURCE_URL=https://mcp.example.com/mcp
   # Your Supabase project's OAuth issuer and public signing-key set.
   OAUTH_ISSUER_URL=https://<project-ref>.supabase.co/auth/v1
   OAUTH_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
   # optional; JSON list, defaults to ["*"]
   CORS_ALLOWED_ORIGINS=["https://app.example.com"]
   ```
4. Run the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Layout

- `app/main.py`: FastAPI app and MCP Streamable HTTP transport wiring
- `app/tools.py`: tool definitions and handlers (`read_context`, `write_context`)
- `app/auth.py`: Bearer-token authentication, returns a typed `AuthenticatedUser`
- `app/oauth.py`: OAuth 2.1 resource-server validation and RFC 9728 metadata
- `app/db.py`: lazily created, shared Supabase client
- `app/config.py`: environment settings

Embeddings are generated with Pinecone inference, using the model configured on the user's Pinecone connection.

## Tests

```bash
pip install -r requirements-dev.txt -c constraints.txt
python -m pytest
```

## OAuth setup

The MCP server is an OAuth **resource server**; Supabase Auth is the authorization
server. Enable **Authentication → OAuth Server** in Supabase and set its
authorization path to `https://<your-web-app>/oauth/consent`. The included Next.js
route displays the client and requested scopes, then calls Supabase to approve or
deny the request.

Configure Supabase with asymmetric signing keys (RS256 or ES256) and, if the MCP
clients you support need it, dynamic client registration. It must issue tokens with:

- `iss` equal to `OAUTH_ISSUER_URL`;
- `aud` equal to `MCP_RESOURCE_URL` (trailing slash is ignored);
- `sub` equal to the Smriti/Supabase user UUID; and
- a `client_id`, proving the token came from an OAuth client rather than a normal
  web-app session.

OAuth-aware MCP clients discover the authorization server from
`/.well-known/oauth-protected-resource`; unauthenticated MCP requests return a
`401` with the required `WWW-Authenticate` challenge. Production deployments must
use HTTPS for both the resource and authorization servers.

Supabase OAuth tokens default to `aud: "authenticated"`. Add a Custom Access
Token Hook which sets `aud` to `MCP_RESOURCE_URL` for OAuth-issued MCP tokens;
the MCP server rejects any other audience. The token `sub` must remain the
Supabase user UUID, which is how Smriti selects the user's Pinecone connection.

## Smoke test

With the server running:

```bash
MCP_ACCESS_TOKEN=<OAuth access token> python test_mcp.py
# or against a deployment
MCP_ACCESS_TOKEN=<OAuth access token> MCP_BASE_URL=https://your-host python test_mcp.py
```
