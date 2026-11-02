'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AlertCircle, ShieldCheck } from 'lucide-react';

import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

type AuthorizationDetails = {
  authorization_id: string;
  client: { name: string; uri: string; logo_uri: string };
  redirect_uri: string;
  scope: string;
};

export default function OAuthConsentPage() {
  const [supabase] = useState(createSupabaseBrowserClient);
  const router = useRouter();
  const searchParams = useSearchParams();
  const authorizationId = searchParams.get('authorization_id');
  const [details, setDetails] = useState<AuthorizationDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const requestId = authorizationId;
    if (!requestId) {
      setError('This authorization request is missing its identifier. Return to your MCP client and try again.');
      return;
    }
    const validRequestId: string = requestId;

    async function loadAuthorization() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.replace(`/login?redirect=${encodeURIComponent(`/oauth/consent?authorization_id=${validRequestId}`)}`);
        return;
      }

      const { data, error: detailsError } = await supabase.auth.oauth.getAuthorizationDetails(validRequestId);
      if (detailsError || !data) {
        setError(detailsError?.message || 'This authorization request is no longer valid.');
        return;
      }
      if (!('authorization_id' in data)) {
        window.location.assign(data.redirect_url);
        return;
      }
      setDetails(data);
    }

    void loadAuthorization();
  }, [authorizationId, router, supabase]);

  const decide = async (decision: 'approve' | 'deny') => {
    if (!authorizationId) return;
    setSubmitting(true);
    const result = decision === 'approve'
      ? await supabase.auth.oauth.approveAuthorization(authorizationId, { skipBrowserRedirect: true })
      : await supabase.auth.oauth.denyAuthorization(authorizationId, { skipBrowserRedirect: true });

    if (result.error || !result.data) {
      setError(result.error?.message || 'We could not complete this authorization request.');
      setSubmitting(false);
      return;
    }
    window.location.assign(result.data.redirect_url);
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary"><ShieldCheck className="h-5 w-5" /></div>
          <CardTitle>Authorize MCP client</CardTitle>
          <CardDescription>Review the client and requested permissions before it can access your Smriti contexts.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {error && <div className="flex gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
          {!error && !details && <div className="py-6 text-center text-sm text-muted-foreground">Loading authorization details…</div>}
          {details && <>
            <dl className="space-y-3 rounded-md border p-4 text-sm">
              <div><dt className="text-muted-foreground">Client</dt><dd className="font-medium">{details.client.name}</dd></div>
              <div><dt className="text-muted-foreground">Redirect URI</dt><dd className="break-all font-mono text-xs">{details.redirect_uri}</dd></div>
              <div><dt className="text-muted-foreground">Requested scopes</dt><dd>{details.scope || 'Basic account access'}</dd></div>
            </dl>
            <p className="text-sm text-muted-foreground">Approving lets this client act through the Smriti MCP as you. You can revoke its access from your OAuth grants.</p>
            <div className="flex justify-end gap-3"><Button variant="outline" disabled={submitting} onClick={() => decide('deny')}>Deny</Button><Button disabled={submitting} onClick={() => decide('approve')}>{submitting ? 'Continuing…' : 'Approve'}</Button></div>
          </>}
        </CardContent>
      </Card>
    </main>
  );
}
