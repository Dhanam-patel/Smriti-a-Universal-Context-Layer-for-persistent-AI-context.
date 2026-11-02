import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { createClient } from '@supabase/supabase-js';
import { cookies } from 'next/headers';
import { Pinecone } from '@pinecone-database/pinecone';

export async function POST(
  request: Request,
  { params }: { params: { chatId: string } }
) {
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
      return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });
    }

    const { chatId } = params;
    const { query } = await request.json();

    if (!query || typeof query !== 'string') {
      return NextResponse.json({ error: { message: 'Query is required' } }, { status: 400 });
    }

    // 1. Verify chat ownership
    const { data: chat, error: chatError } = await supabase
      .from('chats')
      .select('id, pinecone_namespace')
      .eq('id', chatId)
      .eq('user_id', user.id)
      .single();

    if (chatError || !chat) {
      return NextResponse.json({ error: { message: 'Chat not found or access denied' } }, { status: 404 });
    }

    // 2. Resolve Pinecone connection (Use service role to read encrypted_api_key)
    const adminSupabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    );

    const { data: pcConn, error: pcError } = await adminSupabase
      .from('pinecone_connections')
      .select('index_name, host, encrypted_api_key, embedding_model')
      .eq('user_id', user.id)
      .limit(1)
      .single();

    if (pcError || !pcConn) {
      return NextResponse.json({ error: { message: 'Pinecone connection not found' } }, { status: 400 });
    }

    // 3. Generate embedding using Pinecone Inference
    let embedding;
    let pc;
    try {
      pc = new Pinecone({
        apiKey: pcConn.encrypted_api_key,
      });
      const model = pcConn.embedding_model || 'multilingual-e5-large';
      
      const embeddingResponse = await pc.inference.embed({
        model,
        inputs: [query],
        parameters: { inputType: 'query', truncate: 'END' }
      });
      
      // @ts-ignore
      if (!embeddingResponse || !embeddingResponse.data || !embeddingResponse.data[0] || !embeddingResponse.data[0].values) {
        throw new Error("Invalid embedding response");
      }
      // @ts-ignore
      embedding = embeddingResponse.data[0].values;
    } catch (e: any) {
      console.error('Pinecone Inference Error:', e);
      return NextResponse.json({ error: { message: `Failed to generate embedding via Pinecone: ${e?.message || e}` } }, { status: 500 });
    }

    // 4. Search Pinecone
    let searchResults;
    try {
      const index = pc.index(pcConn.index_name);
      const ns = index.namespace(chat.pinecone_namespace);
      
      try {
        const queryResponse = await ns.query({
          vector: embedding,
          topK: 5,
          includeMetadata: true,
        });

        searchResults = queryResponse.matches.map(match => ({
          id: match.id,
          score: match.score,
          content: match.metadata?.content || '',
          metadata: match.metadata,
        }));
      } catch (searchErr: any) {
        const errMsg = String(searchErr?.message || searchErr).toLowerCase();
        if (
          (errMsg.includes('document schema') ||
           errMsg.includes('documents/search') ||
           errMsg.includes('documents api')) &&
          (ns as any).documents
        ) {
          const docResp = await (ns as any).documents.search({
            scoreBy: [{ type: 'dense_vector', field: 'embedding', values: embedding }],
            topK: 5,
            includeFields: ['*'],
          });
          searchResults = (docResp.matches || []).map((match: any) => ({
            id: match._id || match.id,
            score: match._score ?? match.score ?? 0,
            content: match.content || match.text || match.metadata?.content || '',
            metadata: match,
          }));
        } else {
          throw searchErr;
        }
      }
    } catch (e: any) {
      console.error('Pinecone Search Error:', e);
      return NextResponse.json({ error: { message: `Failed to search Pinecone: ${e?.message || e}` } }, { status: 500 });
    }

    return NextResponse.json({ results: searchResults });
  } catch (error: any) {
    console.error('Context Search Error:', error);
    return NextResponse.json(
      { error: { message: 'An unexpected error occurred.' } },
      { status: 500 }
    );
  }
}
