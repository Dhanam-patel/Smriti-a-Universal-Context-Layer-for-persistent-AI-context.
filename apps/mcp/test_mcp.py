"""Manual end-to-end smoke test for the MCP server over Streamable HTTP.

Usage:
    MCP_ACCESS_TOKEN=... python test_mcp.py                       # http://localhost:8000
    MCP_ACCESS_TOKEN=... MCP_BASE_URL=https://host python test_mcp.py
"""

import asyncio
import json
import os
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


def _parse_response_body(response: httpx.Response) -> dict[str, Any] | None:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()

    # Fallback if returned as text/event-stream
    for line in response.text.splitlines():
        if line.startswith("data: "):
            data_str = line[len("data: ") :].strip()
            if data_str.startswith("{"):
                return json.loads(data_str)
    return None


class SmokeTestError(Exception):
    """Raised when the smoke test cannot run or the server does not respond as expected."""


async def main() -> None:
    access_token = os.environ.get("MCP_ACCESS_TOKEN")
    if not access_token:
        raise SmokeTestError("Set MCP_ACCESS_TOKEN to a valid OAuth access token.")

    endpoint = f"{BASE_URL}/mcp"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Initialize
        print(f"Connecting to Streamable HTTP at {endpoint}...")
        init_payload = _rpc(
            "initialize",
            {
                "clientInfo": {"name": "smoke-test", "version": "1.0"},
                "protocolVersion": "2024-11-05",
                "capabilities": {},
            },
            request_id=1,
        )
        init_response = await client.post(endpoint, json=init_payload, headers=headers)
        if init_response.status_code != 200:
            raise SmokeTestError(
                f"Initialize failed: HTTP {init_response.status_code} {init_response.text[:200]}"
            )

        session_id = init_response.headers.get("mcp-session-id")
        init_data = _parse_response_body(init_response)
        print(f"Initialize succeeded. Session ID: {session_id}")
        print("Initialize response:", json.dumps(init_data, indent=2))

        req_headers = dict(headers)
        if session_id:
            req_headers["mcp-session-id"] = session_id

        # 2. Initialized notification
        print("Sending notifications/initialized...")
        notif_response = await client.post(
            endpoint, json=_rpc("notifications/initialized"), headers=req_headers
        )
        if notif_response.status_code not in (200, 202, 204):
            raise SmokeTestError(
                f"Notification failed: HTTP {notif_response.status_code} {notif_response.text[:200]}"
            )
        print(f"Notification accepted (HTTP {notif_response.status_code})")

        # 3. Call tool
        print(f"Calling read_context on chat '{TEST_CHAT}'...")
        tool_payload = _rpc(
            "tools/call",
            {
                "name": "read_context",
                "arguments": {"chat": TEST_CHAT, "query": TEST_QUERY},
            },
            request_id=2,
        )
        tool_response = await client.post(endpoint, json=tool_payload, headers=req_headers)
        if tool_response.status_code != 200:
            raise SmokeTestError(
                f"tools/call failed: HTTP {tool_response.status_code} {tool_response.text[:200]}"
            )

        tool_data = _parse_response_body(tool_response)
        print("Received tool response:", json.dumps(tool_data, indent=2))

        # 4. Cleanly terminate session if stateful
        if session_id:
            print(f"Closing session {session_id}...")
            del_response = await client.delete(
                endpoint,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "mcp-session-id": session_id,
                },
            )
            print(f"Session closed with HTTP {del_response.status_code}")

        print("SUCCESS!")


if __name__ == "__main__":
    asyncio.run(main())
