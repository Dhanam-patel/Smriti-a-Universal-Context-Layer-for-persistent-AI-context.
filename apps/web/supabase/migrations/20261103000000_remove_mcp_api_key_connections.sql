-- OAuth grants are owned and revoked by Supabase Auth. The former table stored
-- only locally-issued, hashed MCP API keys and is no longer part of Smriti's
-- authorization model.
DROP TABLE IF EXISTS public.mcp_connections;
