'use client';

import { useEffect, useState } from 'react';
import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import type { PineconeConnection, McpConnection, Chat } from '@/types/database';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Database, FolderOpen, Plug, Activity, CheckCircle2, XCircle, ArrowRight, Link as LinkIcon } from 'lucide-react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

export default function DashboardPage() {
  const supabase = createSupabaseBrowserClient();
  const [pinecone, setPinecone] = useState<PineconeConnection | null>(null);
  const [mcpConnections, setMcpConnections] = useState<McpConnection[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const [pineconeRes, mcpRes, chatsRes] = await Promise.all([
        supabase.from('pinecone_connections').select('id, index_name, host, embedding_model, status').maybeSingle(),
        supabase.from('mcp_connections').select('*'),
        supabase.from('chats').select('*').order('created_at', { ascending: false }),
      ]);

      setPinecone(pineconeRes.data as PineconeConnection | null);
      setMcpConnections(mcpRes.data || []);
      setChats(chatsRes.data || []);
      setLoading(false);
    }
    loadData();
  }, [supabase]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Overview of your Smriti connections and contexts.
        </p>
      </div>

      {/* Status cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          icon={<Database className="h-5 w-5" />}
          label="Pinecone"
          value={pinecone ? 'Connected' : 'Not connected'}
          connected={!!pinecone}
          href="/settings"
          detail={pinecone?.index_name}
        />
        <StatusCard
          icon={<FolderOpen className="h-5 w-5" />}
          label="Contexts"
          value={`${chats.length} created`}
          connected={chats.length > 0}
          href="/context"
          detail={undefined}
        />
        <StatusCard
          icon={<Plug className="h-5 w-5" />}
          label="MCP Identity"
          value={mcpConnections.length > 0 ? 'Active' : 'Inactive'}
          connected={mcpConnections.length > 0}
          href="/mcp"
          detail={undefined}
        />
        <StatusCard
          icon={<Activity className="h-5 w-5" />}
          label="Status"
          value={pinecone ? 'Ready' : 'Setup needed'}
          connected={!!pinecone}
          href="/settings"
          detail={undefined}
        />
      </div>

      {/* Recent contexts */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Recent Contexts</CardTitle>
          <Link
            href="/context"
            className="flex items-center gap-1 text-sm text-primary hover:underline"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </CardHeader>
        <CardContent>
          {chats.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FolderOpen className="mb-3 h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">No contexts created yet.</p>
              <Link
                href="/context"
                className="mt-3 text-sm text-primary hover:underline"
              >
                Create your first context
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {chats.slice(0, 5).map((chat) => (
                <Link
                  key={chat.id}
                  href={`/context/${chat.id}`}
                  className="flex items-center justify-between rounded-lg border border-border p-3 transition-colors hover:bg-accent"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                      <FolderOpen className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{chat.name}</p>
                      <p className="text-xs text-muted-foreground">
                        /Smriti/{chat.slug}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(chat.created_at), { addSuffix: true })}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Setup guide */}
      {!pinecone && (
        <Card className="border-warning/30 bg-warning/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <LinkIcon className="h-4 w-4 text-warning" />
              Get Started
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <SetupStep
                done={false}
                label="Connect your Pinecone index"
                href="/settings"
              />
              <SetupStep
                done={false}
                label="Create a Smriti context"
                href="/context"
              />
              <SetupStep
                done={false}
                label="Generate an MCP API Key"
                href="/mcp"
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatusCard({
  icon,
  label,
  value,
  connected,
  href,
  detail,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  connected: boolean;
  href: string;
  detail?: string | undefined;
}) {
  return (
    <Link href={href}>
      <Card className="transition-all hover:shadow-md">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              {icon}
            </div>
            {connected ? (
              <Badge className="bg-success/10 text-success hover:bg-success/10">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                Active
              </Badge>
            ) : (
              <Badge variant="secondary">
                <XCircle className="mr-1 h-3 w-3" />
                Inactive
              </Badge>
            )}
          </div>
          <p className="mt-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-1 text-lg font-semibold">{value}</p>
          {detail && (
            <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

function SetupStep({ done, label, href }: { done: boolean; label: string; href: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-accent"
    >
      <div
        className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
          done ? 'bg-success text-success-foreground' : 'border border-border text-muted-foreground'
        }`}
      >
        {done ? <CheckCircle2 className="h-3 w-3" /> : ''}
      </div>
      <span className="text-sm">{label}</span>
      <ArrowRight className="ml-auto h-3 w-3 text-muted-foreground" />
    </Link>
  );
}
