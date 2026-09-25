'use client';

import { useEffect, useState } from 'react';
import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import type { PineconeConnection } from '@/types/database';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { CheckCircle2, AlertCircle, Save, Loader2 } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';

export default function SettingsPage() {
  const supabase = createSupabaseBrowserClient();
  const [pinecone, setPinecone] = useState<PineconeConnection | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Form state
  const [apiKey, setApiKey] = useState('');
  const [indexName, setIndexName] = useState('');
  const [host, setHost] = useState('');
  const [model, setModel] = useState('multilingual-e5-large');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function loadData() {
      const { data } = await supabase
        .from('pinecone_connections')
        .select('id, index_name, host, embedding_model, status')
        .maybeSingle();
      
      setPinecone(data as PineconeConnection | null);
      if (data) {
        setIndexName(data.index_name);
        setHost(data.host || '');
        if (data.embedding_model) setModel(data.embedding_model);
        // We do not get the API key back from the DB, so we leave it blank
      }
      setLoading(false);
    }
    loadData();
  }, [supabase]);

  const handleSave = async () => {
    if (!apiKey.trim() || !indexName.trim() || !host.trim()) {
      toast.error('Please fill in all fields');
      return;
    }
    
    setSaving(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      const res = await fetch('/api/pinecone/connect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          apiKey: apiKey.trim(),
          indexName: indexName.trim(),
          host: host.trim(),
          model: model,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.error?.message || 'Failed to connect to Pinecone');
      } else {
        const data = await res.json();
        toast.success('Successfully connected to Pinecone');
        setPinecone(data.connection);
        setApiKey(''); // Clear the API key for security
      }
    } catch (e: any) {
      console.error(e);
      toast.error('Frontend Error: ' + (e?.message || String(e)));
    }
    setSaving(false);
  };

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
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your external integrations and configuration.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">Pinecone Configuration</CardTitle>
              <CardDescription className="mt-1">
                Connect your vector database to store and retrieve context.
              </CardDescription>
            </div>
            {pinecone ? (
              <Badge className="bg-success/10 text-success hover:bg-success/10">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                Connected
              </Badge>
            ) : (
              <Badge variant="secondary">
                <AlertCircle className="mr-1 h-3 w-3" />
                Not Connected
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              placeholder={pinecone ? "•••••••••••••••• (Leave blank to keep existing)" : "Enter your Pinecone API key"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
          
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="index-name">Index Name</Label>
              <Input
                id="index-name"
                placeholder="e.g. ucl-prototype"
                value={indexName}
                onChange={(e) => setIndexName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="host">Host URL</Label>
              <Input
                id="host"
                placeholder="e.g. your-index-12345.svc.environment.pinecone.io"
                value={host}
                onChange={(e) => setHost(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="model">Embedding Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger id="model">
                <SelectValue placeholder="Select an embedding model" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="multilingual-e5-large">multilingual-e5-large (1024 dimensions)</SelectItem>
                <SelectItem value="llama-text-embed-v2">llama-text-embed-v2 (1024 dimensions)</SelectItem>
                <SelectItem value="bge-large-en-v1.5">bge-large-en-v1.5 (1024 dimensions)</SelectItem>
                <SelectItem value="minilm-l6-v2">minilm-l6-v2 (384 dimensions)</SelectItem>
                <SelectItem value="minilm-l6-v2-hq">minilm-l6-v2-hq (384 dimensions)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              This model will be used via Pinecone's Inference API. Ensure your Pinecone index is configured with the matching dimensions.
            </p>
          </div>

          <Button 
            onClick={handleSave} 
            disabled={saving || (!apiKey && !pinecone) || !indexName || !host || !model}
            className="mt-4"
          >
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {saving ? 'Connecting...' : pinecone ? 'Update Connection' : 'Connect Pinecone'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
