# UCL MCP Server

This is the Python FastAPI server that exposes the Model Context Protocol (MCP) to AI clients.
It allows authenticated AI clients to read and write context to a user's Pinecone vector database.

## Technologies

- Python 3.12+
- FastAPI
- MCP Python SDK (SSE transport)
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
   pip install -r requirements.txt
   ```
3. Configure environment variables in `.env`:
   ```
   SUPABASE_URL=...
   SUPABASE_SERVICE_ROLE_KEY=...

   ```
4. Run the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Layout

- `app/main.py`: FastAPI app and MCP SSE transport wiring
- `app/tools.py`: tool definitions and handlers (`read_context`, `write_context`)
- `app/auth.py`: Bearer-token authentication, returns a typed `AuthenticatedUser`
- `app/db.py`: shared Supabase client
- `app/config.py`: environment settings

Embeddings are generated with Pinecone inference, using the model configured on the user's Pinecone connection.

## Smoke test

With the server running:

```bash
MCP_API_KEY=smr_... python test_mcp.py
# or against a deployment
MCP_API_KEY=smr_... MCP_BASE_URL=https://your-host python test_mcp.py
```
