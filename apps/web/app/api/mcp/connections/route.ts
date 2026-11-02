import { NextResponse } from 'next/server';

const RETIRED_API_KEY_RESPONSE = {
  error: {
    code: 'MCP_API_KEYS_RETIRED',
    message: 'MCP API keys have been replaced by OAuth 2.1. Configure the MCP endpoint in an OAuth-capable client.',
  },
};

export function GET() {
  return NextResponse.json(RETIRED_API_KEY_RESPONSE, { status: 410 });
}

export function POST() {
  return NextResponse.json(RETIRED_API_KEY_RESPONSE, { status: 410 });
}
