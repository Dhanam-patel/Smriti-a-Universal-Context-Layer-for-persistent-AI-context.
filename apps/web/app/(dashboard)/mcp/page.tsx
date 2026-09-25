'use client';

import { useEffect, useState } from 'react';
import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import type { McpConnection } from '@/types/database';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Plug, Copy, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';

export default function MCPPage() {
  const supabase = createSupabaseBrowserClient();
  const [connections, setConnections] = useState<McpConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  
  const [newConnection, setNewConnection] = useState<McpConnection | null>(null);
  const [newSecret, setNewSecret] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const { data: session } = await supabase.auth.getSession();
        const res = await fetch('/api/mcp/connections', {
          headers: {
            Authorization: `Bearer ${session.session?.access_token}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          setConnections(data.connections || []);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [supabase]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const { data: session } = await supabase.auth.getSession();
      
      const res = await fetch('/api/mcp/connections', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.session?.access_token}`,
        },
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.error?.message || 'Failed to create connection');
      } else {
        const data = await res.json();
        toast.success('MCP connection created');
        setConnections([data.connection]);
        setNewConnection(data.connection);
        setNewSecret(data.secret);
      }
    } catch (e) {
      toast.error('An unexpected error occurred');
    }
    setCreating(false);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const mcpServerUrl = typeof window !== 'undefined' ? `${window.location.origin}` : '';

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">MCP Connections</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage credentials for AI agents connecting via the Model Context Protocol.
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={(open) => {
          setCreateOpen(open);
          if (!open) {
            // Clear secret when modal closes
            setNewConnection(null);
            setNewSecret(null);
          }
        }}>
          <DialogTrigger asChild>
            {connections.length === 0 ? (
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Generate API Key
              </Button>
            ) : (
              <div className="hidden"></div>
            )}
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Create MCP Connection</DialogTitle>
            </DialogHeader>
            
            {newSecret && newConnection ? (
              <div className="space-y-4">
                <div className="rounded-md bg-success/10 p-4 text-sm text-success">
                  <p className="font-semibold flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4" /> Connection created successfully!
                  </p>
                  <p className="mt-2 text-success-foreground">
                    Copy these details now. The secret key will never be shown again.
                  </p>
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium">MCP Endpoint</label>
                  <div className="flex gap-2">
                    <Input readOnly value={`${mcpServerUrl}/mcp/sse`} />
                    <Button variant="outline" size="icon" onClick={() => copyToClipboard(`${mcpServerUrl}/mcp/sse`)}>
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Secret Key</label>
                  <div className="flex gap-2">
                    <Input readOnly value={newSecret} />
                    <Button variant="outline" size="icon" onClick={() => copyToClipboard(newSecret)}>
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                <Button className="w-full mt-4" onClick={() => setCreateOpen(false)}>
                  Done
                </Button>
              </div>
            ) : (
              <div className="space-y-4 py-4">
                <p className="text-sm text-muted-foreground">
                  This will generate a new API key that AI agents can use to access your Smriti contexts. Any existing API keys will be permanently revoked.
                </p>
                <Button onClick={handleCreate} disabled={creating} className="w-full">
                  {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {creating ? 'Generating...' : 'Generate Credentials'}
                </Button>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>

      {connections.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Plug className="mb-4 h-12 w-12 text-muted-foreground/40" />
            <h3 className="text-lg font-medium">No API Key Generated</h3>
            <p className="mt-1 text-sm text-muted-foreground max-w-sm">
              Generate an MCP API key to allow external AI applications to securely read and write to your Smriti contexts.
            </p>
            <Button onClick={() => setCreateOpen(true)} className="mt-6">
              <Plus className="mr-2 h-4 w-4" />
              Generate API Key
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="transition-all hover:shadow-md max-w-2xl">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold text-primary">
                MCP Identity Active
              </CardTitle>
              <Badge variant="outline" className="bg-success/5 text-success">
                Active
              </Badge>
            </div>
            <CardDescription>
              Created {formatDistanceToNow(new Date(connections[0].created_at), { addSuffix: true })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground pb-4 border-b">
              <Plug className="h-4 w-4" />
              {connections[0].last_used_at 
                ? `Last used ${formatDistanceToNow(new Date(connections[0].last_used_at), { addSuffix: true })}` 
                : 'Never used'}
            </div>
            
            <div className="space-y-3">
              <p className="text-sm font-medium">Connect your AI Applications</p>
              <div className="bg-muted p-3 rounded-md text-sm font-mono flex items-center justify-between">
                <span>{mcpServerUrl}/mcp/sse</span>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => copyToClipboard(`${mcpServerUrl}/mcp/sse`)}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Use the endpoint above and your API key to configure MCP clients like Claude Desktop.
              </p>
            </div>
            
            <div className="pt-4 flex justify-end">
              <Button variant="outline" onClick={() => setCreateOpen(true)} className="text-destructive border-destructive/30 hover:bg-destructive/10">
                Regenerate API Key
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
