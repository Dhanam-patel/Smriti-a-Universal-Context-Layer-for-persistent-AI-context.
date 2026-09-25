import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { Pinecone } from '@pinecone-database/pinecone';

export async function POST(request: Request) {
  try {
    const cookieStore = cookies();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          },
        },
      }
    );

    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'User is not authenticated' } },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { apiKey, indexName, host, model } = body;

    if (!apiKey || !indexName || !host || !model) {
      return NextResponse.json(
        { error: { code: 'INVALID_INPUT', message: 'Missing required fields' } },
        { status: 400 }
      );
    }

    // 2. Validate Pinecone credentials
    try {
      const pc = new Pinecone({
        apiKey: apiKey,
      });
      // Just check if the index exists or try to describe it
      const index = pc.index(indexName);
      // Optional: Describe index to ensure credentials/host are correct.
      // But just instantiating and describing stats is enough
      await index.describeIndexStats();
    } catch (error) {
      return NextResponse.json(
        { error: { code: 'PINECONE_CONNECTION_FAILED', message: 'Unable to connect to the configured Pinecone index.' } },
        { status: 400 }
      );
    }

    // 3. Store configuration
    // The user has INSERT/UPDATE privileges on pinecone_connections, including encrypted_api_key.
    // Let's check if a connection already exists.
    const { data: existing } = await supabase
      .from('pinecone_connections')
      .select('id')
      .eq('user_id', user.id)
      .maybeSingle();

    let result;
    if (existing) {
      const { data, error } = await supabase
        .from('pinecone_connections')
        .update({
          index_name: indexName,
          host: host,
          encrypted_api_key: apiKey,
          embedding_model: model,
          status: 'active',
          updated_at: new Date().toISOString(),
        })
        .eq('id', existing.id)
        .select('id, user_id, index_name, host, namespace_prefix, embedding_dimension, embedding_model, status, created_at, updated_at')
        .single();
        
      if (error) throw error;
      result = data;
    } else {
      const { data, error } = await supabase
        .from('pinecone_connections')
        .insert({
          user_id: user.id,
          index_name: indexName,
          host: host,
          encrypted_api_key: apiKey,
          embedding_model: model,
          status: 'active',
        })
        .select('id, user_id, index_name, host, namespace_prefix, embedding_dimension, embedding_model, status, created_at, updated_at')
        .single();
        
      if (error) throw error;
      result = data;
    }

    return NextResponse.json({ connection: result });
  } catch (error: any) {
    console.error('Error connecting to Pinecone:', error);
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: error?.message || 'An unexpected error occurred.' } },
      { status: 500 }
    );
  }
}
