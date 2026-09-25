# UCL MCP Server

This is the Python FastAPI server that exposes the Model Context Protocol (MCP) to AI clients.
It allows authenticated AI clients to read and write context to a user's Pinecone vector database.

## Technologies
- Python 3.12+
- FastAPI
- MCP Python SDK (SSE transport)
- Pinecone Python SDK
- OpenAI SDK (for embeddings)
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
   OPENAI_API_KEY=...
   ```
4. Run the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
