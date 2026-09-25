'use client';

import { useEffect, useState } from 'react';
import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import type { Chat, PineconeConnection } from '@/types/database';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { FolderOpen, Plus, ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

export default function ContextPage() {
  const supabase = createSupabaseBrowserClient();
  const router = useRouter();
  const [chats, setChats] = useState<Chat[]>([]);
  const [pinecone, setPinecone] = useState<PineconeConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    async function loadData() {
      const [chatsRes, pineconeRes] = await Promise.all([
        supabase.from('chats').select('*').order('created_at', { ascending: false }),
        supabase.from('pinecone_connections').select('id, index_name, host, embedding_model, status').maybeSingle(),
      ]);
      setChats(chatsRes.data || []);
      setPinecone(pineconeRes.data);
      setLoading(false);
    }
    loadData();
  }, [supabase]);

  const slugify = (text: string) =>
    text
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/[\s_-]+/g, '-')
      .replace(/^-+|-+$/g, '');

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);

    const { data: userData } = await supabase.auth.getUser();
    if (!userData.user) {
      toast.error('Not authenticated');
      setCreating(false);
      return;
    }

    const slug = slugify(newName);

    const { data, error } = await supabase
      .from('chats')
      .insert({
        name: newName.trim(),
        slug,
        pinecone_namespace: slug,
        user_id: userData.user.id,
      })
      .select()
      .single();

    if (error) {
      toast.error(error.message);
      setCreating(false);
      return;
    }

    toast.success(`Context "${newName}" created`);
    setChats([data, ...chats]);
    setNewName('');
    setCreateOpen(false);
    setCreating(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Contexts</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Create and manage isolated Smriti contexts.
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Context
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create a new context</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="name">Context Name</Label>
                <Input
                  id="name"
                  placeholder="e.g. Biodegradable, LLM, Research"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                />
                {newName && (
                  <p className="text-xs text-muted-foreground">
                    Will be accessible as /Smriti/{slugify(newName)}
                  </p>
                )}
              </div>
              {!pinecone && (
                <div className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm">
                  <AlertCircle className="h-4 w-4 text-warning" />
                  <span className="text-muted-foreground">
                    You need to connect Pinecone first.{' '}
                    <Link href="/settings" className="text-primary hover:underline">
                      Go to settings
                    </Link>
                  </span>
                </div>
              )}
              <Button
                onClick={handleCreate}
                disabled={creating || !newName.trim() || !pinecone}
                className="w-full"
              >
                {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {creating ? 'Creating...' : 'Create Context'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Contexts list */}
      {chats.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <FolderOpen className="mb-4 h-12 w-12 text-muted-foreground/40" />
            <h3 className="text-lg font-medium">No contexts created yet</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Create a context to start managing your Smriti knowledge.
            </p>
            <Button
              onClick={() => setCreateOpen(true)}
              className="mt-4"
            >
              <Plus className="mr-2 h-4 w-4" />
              Create your first context
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {chats.map((chat) => (
            <Link key={chat.id} href={`/context/${chat.id}`}>
              <Card className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <FolderOpen className="h-5 w-5 text-primary" />
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <h3 className="mt-3 font-semibold">{chat.name}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    /Smriti/{chat.slug}
                  </p>
                  <p className="mt-3 text-xs text-muted-foreground">
                    Created {formatDistanceToNow(new Date(chat.created_at), { addSuffix: true })}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
