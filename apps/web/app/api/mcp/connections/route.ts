import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import crypto from 'crypto';

export async function GET(request: Request) {
  try {
    const cookieStore = cookies();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() { return cookieStore.getAll(); },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
          },
        },
      }
    );

    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });
    }

    const adminSupabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      {
        cookies: {
          getAll() { return cookieStore.getAll(); },
          setAll() {},
        },
      }
    );

    const { data: connections, error } = await adminSupabase
      .from('mcp_connections')
      .select('id, user_id, status, created_at, last_used_at')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false });

    if (error) {
      return NextResponse.json({ error: { message: 'Failed to fetch connections' } }, { status: 500 });
    }

    return NextResponse.json({ connections: connections || [] });
  } catch (error: any) {
    return NextResponse.json({ error: { message: 'An unexpected error occurred.' } }, { status: 500 });
  }
}

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

    // Delete any existing connections for this user (Revocation via regeneration)
    // We use the service role key to bypass potential RLS restrictions on DELETE
    const adminSupabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      {
        cookies: {
          getAll() { return cookieStore.getAll(); },
          setAll() {},
        },
      }
    );

    await adminSupabase
      .from('mcp_connections')
      .delete()
      .eq('user_id', user.id);

    // Generate secure API Key
    const randomHex = crypto.randomBytes(24).toString('hex');
    const secret = `smr_${randomHex}`;
    
    // Hash credential for storage
    const credentialHash = crypto.createHash('sha256').update(secret).digest('hex');

    // Insert into mcp_connections (we can leave connection_id as just 'mcp' or a dummy since it's not used in URLs anymore, but let's keep it non-null)
    const { data: connection, error } = await supabase
      .from('mcp_connections')
      .insert({
        user_id: user.id,
        connection_id: 'default',
        credential_hash: credentialHash,
        status: 'active',
      })
      .select('id, user_id, status, created_at, last_used_at')
      .single();

    if (error) {
      console.error('Database Error:', error);
      return NextResponse.json({ error: { message: 'Failed to create MCP connection' } }, { status: 500 });
    }

    // Return connection and the ONE-TIME secret API key
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
