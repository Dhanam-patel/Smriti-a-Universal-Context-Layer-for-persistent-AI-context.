const { createClient } = require('@supabase/supabase-js');
const crypto = require('crypto');
require('dotenv').config({ path: 'apps/web/.env' });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

const supabase = createClient(supabaseUrl, supabaseKey);

async function testInsert() {
  const randomHex = crypto.randomBytes(24).toString('hex');
  const secret = `smr_${randomHex}`;
  const credentialHash = crypto.createHash('sha256').update(secret).digest('hex');

  // Hardcode a user_id from the database for testing or just test the insert schema.
  // Wait, without a valid user_id it will fail foreign key constraint. Let's fetch a user_id first.
  const { data: users, error: userError } = await supabase.auth.admin.listUsers();
  if (userError || !users.users.length) {
    console.error('Failed to get user:', userError);
    return;
  }
  const userId = users.users[0].id;

  console.log('Testing insert for user:', userId);

  const { data: connection, error } = await supabase
    .from('mcp_connections')
    .insert({
      user_id: userId,
      connection_id: 'default',
      credential_hash: credentialHash,
      status: 'active',
    })
    .select('id, user_id, status, created_at, last_used_at')
    .single();

  if (error) {
    console.error('Database Error:', error);
  } else {
    console.log('Success:', connection);
  }
}

testInsert();
