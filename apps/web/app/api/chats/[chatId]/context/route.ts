import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { createClient } from '@supabase/supabase-js';
import { cookies } from 'next/headers';
import { Pinecone } from '@pinecone-database/pinecone';
import crypto from 'crypto';

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
    const { content } = await request.json();

    if (!content || typeof content !== 'string') {
      return NextResponse.json({ error: { message: 'Content is required' } }, { status: 400 });
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
      console.error('Pinecone connection error:', pcError);
      return NextResponse.json({ error: { message: `Pinecone connection not found: ${pcError?.message}` } }, { status: 400 });
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
        inputs: [content],
        parameters: { inputType: 'passage', truncate: 'END' }
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

    // 4. Upsert into Pinecone
    try {
      const index = pc.index(pcConn.index_name);
      const ns = index.namespace(chat.pinecone_namespace);
      
      const recordId = `ctx_${crypto.randomUUID()}`;
      const now = new Date().toISOString();
      
      try {
        // @ts-ignore
        await ns.upsert({
          records: [{
            id: recordId,
            values: embedding,
            metadata: {
              content,
              source: 'dashboard',
              created_at: now,
              updated_at: now,
            }
          }]
        });
      } catch (upsertErr: any) {
        const errMsg = String(upsertErr?.message || upsertErr).toLowerCase();
        if (
          (errMsg.includes('document schema') ||
           errMsg.includes('documents/upsert') ||
           errMsg.includes('documents api')) &&
          (ns as any).documents
        ) {
          let desc: any = null;
          try {
            desc = await pc.describeIndex(pcConn.index_name);
          } catch {}
          const fields = desc?.schema?.fields || {};
          let denseField: string | null = null;
          const textFields: string[] = [];

          for (const [name, def] of Object.entries<any>(fields)) {
            const type = def?.type || '';
            const typeName = def?.constructor?.name || '';
            if (type === 'dense_vector' || typeName.includes('DenseVector')) {
              if (!denseField) denseField = name;
            } else if (
              type === 'string' ||
              type === 'semantic_text' ||
              typeName.includes('String') ||
              typeName.includes('SemanticText')
            ) {
              textFields.push(name);
            }
          }

          const doc: Record<string, any> = {
            _id: recordId,
            source: 'dashboard',
            created_at: now,
            updated_at: now,
          };

          // Only store embedding in the schema's dense_vector field if present
          if (denseField) {
            doc[denseField] = embedding;
          }

          if (textFields.length > 0) {
            for (const f of textFields) {
              doc[f] = content;
            }
          } else {
            doc.content = content;
            doc.text = content;
          }

          if (!doc.content) {
            doc.content = content;
          }

          await (ns as any).documents.upsert({
            documents: [doc],
          });
        } else {
          throw upsertErr;
        }
      }
    } catch (e: any) {
      console.error('Pinecone Error:', e);
      return NextResponse.json({ error: { message: `Failed to write to Pinecone: ${e?.message || e}` } }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error('Context Write Error:', error);
    return NextResponse.json(
      { error: { message: error?.message || 'An unexpected error occurred.' } },
      { status: 500 }
    );
  }
}
