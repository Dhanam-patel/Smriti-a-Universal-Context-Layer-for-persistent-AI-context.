"""Manual end-to-end smoke test for the MCP server over SSE.

Usage:
    MCP_API_KEY=smr_... python test_mcp.py                       # http://localhost:8000
    MCP_API_KEY=smr_... MCP_BASE_URL=https://host python test_mcp.py
"""

import asyncio
import json
import os
import sys
from typing import Any

import httpx

BASE_URL = os.environ.get("MCP_BASE_URL", "http://localhost:8000").rstrip("/")
TEST_CHAT = os.environ.get("MCP_TEST_CHAT", "test-1")
TEST_QUERY = os.environ.get("MCP_TEST_QUERY", "smriti")


def _rpc(
    method: str, params: dict[str, Any] | None = None, request_id: int | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        payload["id"] = request_id
    if params is not None:
        payload["params"] = params
    return payload


async def main() -> int:
    api_key = os.environ.get("MCP_API_KEY")
    if not api_key:
        print("Set MCP_API_KEY to a valid MCP credential.", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def post(post_url: str, payload: dict[str, Any]) -> None:
            await client.post(f"{BASE_URL}{post_url}", json=payload, headers=headers)

        print("Connecting to SSE...")
        async with client.stream(
            "GET", f"{BASE_URL}/mcp/sse", headers=headers
        ) as response:
            post_url: str | None = None

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[len("data: ") :]

                # The first data line is the endpoint to POST messages to.
                if post_url is None:
                    post_url = data_str
                    print(f"Endpoint received: {post_url}")
                    await post(
                        post_url,
                        _rpc(
                            "initialize",
                            {
                                "clientInfo": {"name": "test", "version": "1.0"},
                                "protocolVersion": "2024-11-05",
                            },
                            request_id=1,
                        ),
                    )
                    print("Sent initialize!")
                    continue

                if not data_str.startswith("{"):
                    continue
                data = json.loads(data_str)
                print("Received message:", json.dumps(data, indent=2))

                if data.get("id") == 1:
                    await post(post_url, _rpc("notifications/initialized"))
                    print("Sent initialized notification!")
                    await post(
                        post_url,
                        _rpc(
                            "tools/call",
                            {
                                "name": "read_context",
                                "arguments": {"chat": TEST_CHAT, "query": TEST_QUERY},
                            },
                            request_id=2,
                        ),
                    )
                    print("Sent tools/call!")
                elif data.get("id") == 2:
                    print("SUCCESS!")
                    return 0

    print("Stream ended without a tools/call response.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
