'use client';

import { useEffect, useState } from 'react';
import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import type { Chat, ContextResult } from '@/types/database';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ArrowLeft, Search, Send, AlertCircle, FileText, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';

export default function ContextDetailPage() {
  const params = useParams();
  const chatId = params.chatId as string;
  const supabase = createSupabaseBrowserClient();
  const [chat, setChat] = useState<Chat | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ContextResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [writeContent, setWriteContent] = useState('');
  const [writing, setWriting] = useState(false);

  useEffect(() => {
    async function loadChat() {
      const { data } = await supabase
        .from('chats')
        .select('*')
        .eq('id', chatId)
        .maybeSingle();
      setChat(data);
      setLoading(false);
    }
    loadChat();
  }, [supabase, chatId]);

  const handleSearch = async () => {
    if (!query.trim() || !chat) return;
    setSearching(true);
    setHasSearched(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`/api/chats/${chatId}/context/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.error?.message || 'Search failed');
        setResults([]);
      } else {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch {
      toast.error('Unable to search context');
      setResults([]);
    }

    setSearching(false);
  };

  const handleWrite = async () => {
    if (!writeContent.trim() || !chat) return;
    setWriting(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`/api/chats/${chatId}/context`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ content: writeContent.trim() }),
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.error?.message || 'Write failed');
      } else {
        toast.success('Context written successfully');
        setWriteContent('');
      }
    } catch {
      toast.error('Unable to write context');
    }

    setWriting(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!chat) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="mb-4 h-10 w-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">Context not found.</p>
        <Link href="/context" className="mt-3 text-sm text-primary hover:underline">
          Back to contexts
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <Link
          href="/context"
          className="mb-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to contexts
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">{chat.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Namespace: {chat.pinecone_namespace} · /Smriti/{chat.slug}
        </p>
      </div>

      {/* Write context */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Write Context</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Label htmlFor="write-content">Add new context to this namespace</Label>
          <Textarea
            id="write-content"
            placeholder="Enter the information you want to store..."
            value={writeContent}
            onChange={(e) => setWriteContent(e.target.value)}
            rows={4}
          />
          <Button
            onClick={handleWrite}
            disabled={!writeContent.trim() || writing}
          >
            {writing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
            {writing ? 'Writing...' : 'Write to Context'}
          </Button>
        </CardContent>
      </Card>

      {/* Search / Read context */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Search Context</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Label htmlFor="search-query">Semantic search across this namespace</Label>
          <div className="flex gap-2">
            <Input
              id="search-query"
              placeholder="What did we discuss about PLA?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch} disabled={!query.trim() || searching}>
              {searching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              {searching ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {/* Results */}
          {hasSearched && !searching && (
            <div className="mt-4 space-y-3">
              {results.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <FileText className="mb-2 h-8 w-8 text-muted-foreground/40" />
                  <p className="text-sm text-muted-foreground">
                    No matching context found. Try a different query.
                  </p>
                </div>
              ) : (
                results.map((result, idx) => (
                  <div
                    key={result.id || idx}
                    className="rounded-lg border border-border p-4 animate-slide-up"
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <Badge variant="secondary">
                        Score: {(result.score * 100).toFixed(1)}%
                      </Badge>
                      {Boolean(result.metadata?.created_at) && (
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(
                            new Date(result.metadata.created_at as string),
                            { addSuffix: true }
                          )}
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed">{result.content}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
