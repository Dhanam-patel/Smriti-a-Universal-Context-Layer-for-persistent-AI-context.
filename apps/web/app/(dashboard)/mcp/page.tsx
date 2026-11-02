'use client';

import { Copy, Plug, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function MCPPage() {
  const mcpServerUrl = process.env.NEXT_PUBLIC_MCP_SERVER_URL || 'https://smriti-ucl-mcp.vercel.app';
  const endpoint = `${mcpServerUrl}/mcp`;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">MCP Connection</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Connect an OAuth-capable MCP client to your Smriti contexts.
        </p>
      </div>

      <Card className="transition-all hover:shadow-md">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-primary">OAuth 2.1 protected</CardTitle>
            <Badge variant="outline" className="bg-success/5 text-success">Ready to connect</Badge>
          </div>
          <CardDescription>
            Your MCP client signs in through the configured authorization provider; Smriti never displays a long-lived MCP API key.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <p className="text-sm font-medium">MCP endpoint</p>
            <div className="bg-muted p-3 rounded-md text-sm font-mono flex items-center justify-between gap-3">
              <span className="truncate">{endpoint}</span>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => copyToClipboard(endpoint)} aria-label="Copy MCP endpoint">
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="rounded-md border p-4 text-sm text-muted-foreground space-y-2">
            <p className="font-medium text-foreground flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> How to connect</p>
            <p>Add the endpoint in an MCP client that supports OAuth authorization. When it connects, the client discovers Smriti&apos;s authorization metadata and opens your normal sign-in and consent flow.</p>
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Plug className="h-4 w-4" />
            Access is scoped to the signed-in Smriti user&apos;s contexts.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
