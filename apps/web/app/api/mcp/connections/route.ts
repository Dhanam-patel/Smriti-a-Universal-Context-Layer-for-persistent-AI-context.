import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import crypto from 'crypto';

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
      return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });
    }

    // Generate opaque connection ID
    const connectionId = `cn_${crypto.randomBytes(8).toString('hex')}`;
    
    // Generate secure credential
    const secret = crypto.randomBytes(32).toString('hex');
    
    // Hash credential for storage
    const credentialHash = crypto.createHash('sha256').update(secret).digest('hex');

    // Insert into mcp_connections
    const { data: connection, error } = await supabase
      .from('mcp_connections')
      .insert({
        user_id: user.id,
        connection_id: connectionId,
        credential_hash: credentialHash,
        status: 'active',
      })
      .select('id, user_id, connection_id, status, created_at, last_used_at')
      .single();

    if (error) {
      console.error('Database Error:', error);
      return NextResponse.json({ error: { message: 'Failed to create MCP connection' } }, { status: 500 });
    }

    // Return connection and the ONE-TIME secret
    return NextResponse.json({
      connection,
      secret,
    });
  } catch (error: any) {
    console.error('MCP Connection Error:', error);
    return NextResponse.json(
      { error: { message: 'An unexpected error occurred.' } },
      { status: 500 }
    );
  }
}
