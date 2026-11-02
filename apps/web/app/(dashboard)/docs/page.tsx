'use client';

import { Copy } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function DocsPage() {
  const mcpServerUrl = process.env.NEXT_PUBLIC_MCP_SERVER_URL || 'https://smriti-ucl-mcp.vercel.app';
  const endpoint = `${mcpServerUrl}/mcp`;
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Documentation</h1>
        <p className="mt-1 text-sm text-muted-foreground">Connect your MCP client and use Smriti&apos;s isolated contexts.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>1. Connect with OAuth</CardTitle>
          <CardDescription>Use an MCP client that supports OAuth authorization and Streamable HTTP; no API key or Authorization header is required in its configuration.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>Add this Streamable HTTP endpoint as a remote MCP server. On first connection, your client discovers Smriti&apos;s OAuth 2.1 metadata and opens the sign-in and consent flow.</p>
          <div className="relative"><pre className="bg-muted p-4 rounded-md text-sm overflow-x-auto"><code>{endpoint}</code></pre><Button variant="outline" size="icon" className="absolute top-2 right-2 h-8 w-8" onClick={() => copyToClipboard(endpoint)} aria-label="Copy MCP endpoint"><Copy className="h-4 w-4" /></Button></div>
          <p>Choose the same identity that owns your Smriti contexts. Tokens are short-lived and are managed by the MCP client.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>2. Specifying contexts</CardTitle><CardDescription>Keep separate memory contexts for different projects and conversations.</CardDescription></CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground"><p>Tell your agent which context to use with:</p><div className="bg-muted p-3 rounded-md font-mono text-foreground">/UCL/&lt;chat-name&gt;</div><p><strong>Example:</strong> &quot;Please summarize our previous discussion /UCL/project-alpha&quot;</p></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>3. Available tools</CardTitle><CardDescription>The MCP server provides two tools for your vector database.</CardDescription></CardHeader>
        <CardContent className="space-y-6 text-sm text-muted-foreground">
          <div className="space-y-2 border-l-2 border-primary pl-4"><h3 className="font-semibold text-foreground">read_context</h3><p>Search semantic memory relevant to the current prompt.</p><div className="text-xs font-mono bg-muted p-2 rounded">Parameters: chat (string), query (string)</div></div>
          <div className="space-y-2 border-l-2 border-primary pl-4"><h3 className="font-semibold text-foreground">write_context</h3><p>Save insights, code snippets, or memories into a context.</p><div className="text-xs font-mono bg-muted p-2 rounded">Parameters: chat (string), content (string)</div></div>
        </CardContent>
      </Card>
    </div>
  );
}
