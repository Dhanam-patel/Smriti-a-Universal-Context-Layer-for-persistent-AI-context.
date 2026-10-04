'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function DocsPage() {
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  // Use the hosted MCP server URL
  const mcpServerUrl = process.env.NEXT_PUBLIC_MCP_SERVER_URL || 'https://smriti-ucl-mcp.vercel.app';
  
  const mcpRemoteConfigCode = `{
  "mcpServers": {
    "Smriti": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "${mcpServerUrl}/mcp/sse",
        "--header",
        "Authorization: Bearer smr_YOUR_GENERATED_API_KEY"
      ]
    }
  }
}`;

  const cursorCommand = `npx -y mcp-remote ${mcpServerUrl}/mcp/sse --header "Authorization: Bearer smr_YOUR_GENERATED_API_KEY"`;

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Documentation</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Learn how to integrate and use the Smriti Universal Context Layer (UCL).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>1. Connecting to the MCP</CardTitle>
          <CardDescription>
            Select your IDE or tool to see how to add the Smriti MCP. Make sure to replace the API key placeholder with your actual generated key.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="antigravity" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="antigravity">AntiGravity IDE</TabsTrigger>
              <TabsTrigger value="cursor">Cursor IDE</TabsTrigger>
            </TabsList>
            
            <TabsContent value="antigravity" className="space-y-4">
              <p className="text-sm text-muted-foreground">Add this to your <code>mcp_config.json</code> file.</p>
              <div className="relative">
                <pre className="bg-muted p-4 rounded-md text-sm overflow-x-auto">
                  <code>{mcpRemoteConfigCode}</code>
                </pre>
                <Button
                  variant="outline" size="icon"
                  className="absolute top-2 right-2 h-8 w-8"
                  onClick={() => copyToClipboard(mcpRemoteConfigCode)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </TabsContent>
            
            <TabsContent value="cursor" className="space-y-4">
              <p className="text-sm text-muted-foreground">
                In Cursor, go to <strong>Settings &gt; Features &gt; MCP</strong> and add a new server.
                <br />Set the type to <code>command</code> and paste the following:
              </p>
              <div className="relative">
                <pre className="bg-muted p-4 rounded-md text-sm overflow-x-auto whitespace-pre-wrap">
                  <code>{cursorCommand}</code>
                </pre>
                <Button
                  variant="outline" size="icon"
                  className="absolute top-2 right-2 h-8 w-8"
                  onClick={() => copyToClipboard(cursorCommand)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </TabsContent>

          </Tabs>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2. Specifying Contexts</CardTitle>
          <CardDescription>
            Smriti allows you to maintain completely separate memory contexts (or chats).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            When prompting your AI agent, you can tell it to use a specific context by including a special keyword in your prompt:
          </p>
          <div className="bg-muted p-3 rounded-md font-mono text-foreground">
            /UCL/&lt;chat-name&gt;
          </div>
          <p>
            <strong>Example:</strong> "Please summarize our previous discussion /UCL/project-alpha"
          </p>
          <p>
            The AI agent will extract the chat name (e.g., <code>project-alpha</code>) and pass it to the MCP tools to access the exact isolated vector namespace associated with that chat.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>3. Available Tools</CardTitle>
          <CardDescription>
            The Smriti MCP currently provides two core tools for agents to interact with your vector database.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2 border-l-2 border-primary pl-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              read_context
            </h3>
            <p className="text-sm text-muted-foreground">
              Allows the AI to search your semantic memory to retrieve information relevant to your current prompt.
            </p>
            <div className="text-xs font-mono bg-muted p-2 rounded">
              Parameters: <br/>
              - chat (string): The UCL chat slug.<br/>
              - query (string): The search query to embed and look up.
            </div>
          </div>

          <div className="space-y-2 border-l-2 border-primary pl-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              write_context
            </h3>
            <p className="text-sm text-muted-foreground">
              Allows the AI to permanently save new insights, code snippets, or memories into your vector index for future retrieval.
            </p>
            <div className="text-xs font-mono bg-muted p-2 rounded">
              Parameters: <br/>
              - chat (string): The UCL chat slug.<br/>
              - content (string): The text content to embed and save.
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>4. Features</CardTitle>
          <CardDescription>
            What you get with Smriti UCL.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 space-y-2 text-sm text-muted-foreground">
            <li><strong>Isolated Contexts:</strong> Keep different projects, domains, and conversations strictly separated using isolated Pinecone namespaces.</li>
            <li><strong>Single Identity Model:</strong> Manage everything from a single API key rather than deploying separate servers for different projects.</li>
            <li><strong>Universal Compatibility:</strong> Works seamlessly with any MCP-compatible AI agent or IDE without complex setups.</li>
            <li><strong>Dashboard Sync:</strong> Any memory written by an AI agent is instantly accessible and manageable through your web dashboard.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
