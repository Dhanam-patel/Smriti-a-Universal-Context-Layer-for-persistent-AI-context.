export type Profile = {
  id: string;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
};

export type PineconeConnection = {
  id: string;
  user_id: string;
  index_name: string;
  host: string | null;
  namespace_prefix: string | null;
  embedding_dimension: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export type McpConnection = {
  id: string;
  user_id: string;
  connection_id: string;
  status: string;
  created_at: string;
  last_used_at: string | null;
};

export type Chat = {
  id: string;
  user_id: string;
  name: string;
  slug: string;
  pinecone_namespace: string;
  created_at: string;
  updated_at: string;
};

export type ContextResult = {
  id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
};
