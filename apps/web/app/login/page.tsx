'use client';

import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import { Layers, Chrome } from 'lucide-react';
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';

export default function LoginPage() {
  const supabase = createSupabaseBrowserClient();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);

  const redirectTo = searchParams.get('redirect') || '/dashboard';
  const origin = typeof window !== 'undefined' ? window.location.origin : '';

  const handleGoogleLogin = async () => {
    setLoading(true);
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${origin}/auth/callback?redirect=${redirectTo}`,
      },
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Layers className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            Smriti
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to manage your contexts and MCP connections.
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-border bg-white px-4 py-3 text-sm font-medium text-slate-700 transition-all hover:bg-slate-50 hover:shadow-sm disabled:opacity-50 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <Chrome className="h-5 w-5" />
            {loading ? 'Connecting...' : 'Continue with Google'}
          </button>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            By continuing, you agree to the Smriti terms of service and acknowledge
            our privacy policy.
          </p>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Smriti Prototype — Google authentication required
        </p>
      </div>
    </div>
  );
}
