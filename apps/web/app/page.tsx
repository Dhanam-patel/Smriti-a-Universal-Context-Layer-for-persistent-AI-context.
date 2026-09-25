import { createSupabaseServerClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import { Database, Zap, Globe, Shield, ArrowRight, Layers } from 'lucide-react';
import Link from 'next/link';

export default async function LandingPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) {
    redirect('/dashboard');
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900">
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Layers className="h-5 w-5" />
            </div>
            <span className="text-lg font-semibold tracking-tight">Smriti</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/docs"
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Docs
            </Link>
            <Link
              href="/login"
              className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Sign in
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-7xl px-6 py-20 sm:py-32">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground animate-fade-in">
              <Zap className="h-3.5 w-3.5 text-primary" />
              Smriti, a Universal Context Layer for persistent AI context
            </div>
            <h1 className="text-4xl font-bold tracking-tight sm:text-6xl animate-slide-up">
              Your vector database,
              <br />
              <span className="text-primary">connected to any AI agent.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground animate-slide-up">
              Smriti lets you connect your Pinecone vector database, create isolated
              contexts, and expose them to AI applications through MCP. One
              persistent memory layer, accessible everywhere.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4 animate-slide-up">
              <Link
                href="/login"
                className="inline-flex h-11 items-center justify-center rounded-lg bg-primary px-6 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/25"
              >
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="/docs"
                className="inline-flex h-11 items-center justify-center rounded-lg border border-border bg-card px-6 text-sm font-medium transition-colors hover:bg-accent"
              >
                Learn More
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border/40 bg-card/50">
        <div className="mx-auto max-w-7xl px-6 py-20">
          <div className="grid gap-8 sm:grid-cols-3">
            <FeatureCard
              icon={<Database className="h-6 w-6 text-primary" />}
              title="Bring Your Own Pinecone"
              description="Connect your existing Pinecone index. Smriti manages access — it never replaces your infrastructure."
            />
            <FeatureCard
              icon={<Globe className="h-6 w-6 text-primary" />}
              title="MCP Access Layer"
              description="Expose your contexts to any MCP-compatible AI application with a single connection endpoint."
            />
            <FeatureCard
              icon={<Shield className="h-6 w-6 text-primary" />}
              title="Isolated & Secure"
              description="Each context maps to a Pinecone namespace. Users, connections, and contexts are fully isolated."
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border/40">
        <div className="mx-auto max-w-4xl px-6 py-20">
          <h2 className="text-center text-3xl font-bold tracking-tight">
            How it works
          </h2>
          <div className="mt-12 space-y-6">
            <Step
              num={1}
              title="Sign in with Google"
              description="Create your Smriti account with Google authentication."
            />
            <Step
              num={2}
              title="Connect your Pinecone"
              description="Provide your Pinecone API key and index name. Smriti validates the connection."
            />
            <Step
              num={3}
              title="Create contexts"
              description="Create isolated Smriti contexts like 'LLM', 'Biodegradable', or 'Research'. Each maps to a Pinecone namespace."
            />
            <Step
              num={4}
              title="Create an MCP connection"
              description="Generate a user-specific MCP endpoint with authentication credentials."
            />
            <Step
              num={5}
              title="Connect your AI"
              description="Point any MCP-compatible AI client to your Smriti endpoint. Use /Smriti/chat to select a context."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-8">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-primary text-primary-foreground">
              <Layers className="h-4 w-4" />
            </div>
            <span className="text-sm font-medium">Smriti</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Smriti — Prototype
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 transition-all hover:shadow-md">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
        {icon}
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function Step({
  num,
  title,
  description,
}: {
  num: number;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
        {num}
      </div>
      <div className="pt-1.5">
        <h3 className="font-semibold">{title}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
