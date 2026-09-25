/*
# UCL Control-Plane Schema

Creates the four control-plane tables for the Universal Context Layer prototype:
profiles, pinecone_connections, mcp_connections, and chats.

1. New Tables
- `profiles`: extends auth.users with display name and avatar URL. Auto-created via trigger on auth.users INSERT.
- `pinecone_connections`: stores per-user Pinecone configuration (index name, host, API key, embedding dimension, status). The encrypted_api_key column is hidden from anon/authenticated via column-level GRANT/REVOKE.
- `mcp_connections`: stores per-user MCP connection with opaque connection_id and hashed credential. The credential_hash column is hidden from anon/authenticated.
- `chats`: stores per-user UCL contexts with name, slug, and Pinecone namespace mapping.

2. Security
- RLS enabled on all tables.
- profiles: users can read/update their own profile.
- pinecone_connections: users can CRUD their own rows, but the encrypted_api_key column is only readable by the service role (column-level GRANT/REVOKE).
- mcp_connections: users can CRUD their own rows, but the credential_hash column is only readable by the service role.
- chats: users can CRUD their own rows.
- All policies use auth.uid() for ownership checks.

3. Triggers
- `handle_new_user`: creates a profile row when a new auth.users row is inserted.
- `update_updated_at`: auto-updates updated_at on row modification (profiles, pinecone_connections, chats).

4. Important Notes
- The encrypted_api_key is stored as-is (not additionally encrypted) because it is protected by column-level privileges and only the service role (which bypasses RLS) can read it. Server-side API routes use the service role key to access it.
- The mcp_connections.credential_hash stores a SHA-256 hash of the plaintext credential. The plaintext is shown to the user once at creation time and never stored.
- Chat slugs are unique per user. The pinecone_namespace defaults to the slug value.
*/

-- ============================================
-- PROFILES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name text,
  avatar_url text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_own_profile" ON profiles;
CREATE POLICY "select_own_profile" ON profiles FOR SELECT
  TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "update_own_profile" ON profiles;
CREATE POLICY "update_own_profile" ON profiles FOR UPDATE
  TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- ============================================
-- PINECONE CONNECTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS pinecone_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  index_name text NOT NULL,
  host text,
  namespace_prefix text DEFAULT '',
  encrypted_api_key text NOT NULL,
  embedding_dimension integer NOT NULL DEFAULT 1536,
  embedding_model text NOT NULL DEFAULT 'multilingual-e5-large',
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE pinecone_connections ENABLE ROW LEVEL SECURITY;

-- Column-level security: revoke all, then grant only safe columns
REVOKE ALL ON pinecone_connections FROM anon, authenticated;
GRANT SELECT (id, user_id, index_name, host, namespace_prefix, encrypted_api_key, embedding_dimension, embedding_model, status, created_at, updated_at) ON pinecone_connections TO service_role;
GRANT SELECT (id, user_id, index_name, host, namespace_prefix, embedding_dimension, embedding_model, status, created_at, updated_at) ON pinecone_connections TO authenticated;
GRANT INSERT (id, user_id, index_name, host, namespace_prefix, encrypted_api_key, embedding_dimension, embedding_model, status, created_at, updated_at) ON pinecone_connections TO authenticated;
GRANT UPDATE (id, user_id, index_name, host, namespace_prefix, encrypted_api_key, embedding_dimension, embedding_model, status, created_at, updated_at) ON pinecone_connections TO authenticated;
GRANT DELETE ON pinecone_connections TO authenticated;

DROP POLICY IF EXISTS "select_own_pinecone" ON pinecone_connections;
CREATE POLICY "select_own_pinecone" ON pinecone_connections FOR SELECT
  TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "insert_own_pinecone" ON pinecone_connections;
CREATE POLICY "insert_own_pinecone" ON pinecone_connections FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_own_pinecone" ON pinecone_connections;
CREATE POLICY "update_own_pinecone" ON pinecone_connections FOR UPDATE
  TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_pinecone" ON pinecone_connections;
CREATE POLICY "delete_own_pinecone" ON pinecone_connections FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

-- ============================================
-- MCP CONNECTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS mcp_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  connection_id text NOT NULL UNIQUE,
  credential_hash text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz
);

ALTER TABLE mcp_connections ENABLE ROW LEVEL SECURITY;

-- Column-level security: hide credential_hash from frontend
REVOKE ALL ON mcp_connections FROM anon, authenticated;
GRANT SELECT (id, user_id, connection_id, status, created_at, last_used_at) ON mcp_connections TO authenticated;
GRANT INSERT (id, user_id, connection_id, credential_hash, status, created_at, last_used_at) ON mcp_connections TO authenticated;
GRANT UPDATE (id, user_id, connection_id, credential_hash, status, created_at, last_used_at) ON mcp_connections TO authenticated;
GRANT DELETE ON mcp_connections TO authenticated;

DROP POLICY IF EXISTS "select_own_mcp" ON mcp_connections;
CREATE POLICY "select_own_mcp" ON mcp_connections FOR SELECT
  TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "insert_own_mcp" ON mcp_connections;
CREATE POLICY "insert_own_mcp" ON mcp_connections FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_own_mcp" ON mcp_connections;
CREATE POLICY "update_own_mcp" ON mcp_connections FOR UPDATE
  TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_mcp" ON mcp_connections;
CREATE POLICY "delete_own_mcp" ON mcp_connections FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

-- ============================================
-- CHATS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS chats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  slug text NOT NULL,
  pinecone_namespace text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, slug)
);

ALTER TABLE chats ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_own_chats" ON chats;
CREATE POLICY "select_own_chats" ON chats FOR SELECT
  TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "insert_own_chats" ON chats;
CREATE POLICY "insert_own_chats" ON chats FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_own_chats" ON chats;
CREATE POLICY "update_own_chats" ON chats FOR UPDATE
  TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_chats" ON chats;
CREATE POLICY "delete_own_chats" ON chats FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

-- ============================================
-- TRIGGERS
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, avatar_url)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
    COALESCE(NEW.raw_user_meta_data->>'avatar_url', '')
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS profiles_updated_at ON profiles;
CREATE TRIGGER profiles_updated_at BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS pinecone_connections_updated_at ON pinecone_connections;
CREATE TRIGGER pinecone_connections_updated_at BEFORE UPDATE ON pinecone_connections
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS chats_updated_at ON chats;
CREATE TRIGGER chats_updated_at BEFORE UPDATE ON chats
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_pinecone_connections_user_id ON pinecone_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_connections_user_id ON mcp_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_connections_connection_id ON mcp_connections(connection_id);
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);