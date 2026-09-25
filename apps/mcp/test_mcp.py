import asyncio
import httpx
import json

async def main():
    api_key = "smr_9472ca56e3019e21f10edef52e125dd4b74530914a78cb36"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Connect to SSE and get session ID
        print("Connecting to SSE...")
        async with client.stream("GET", "http://localhost:8000/mcp/sse", headers=headers) as response:
            session_id = None
            post_url = None
            
            async for line in response.aiter_lines():
                if line.startswith("event: endpoint"):
                    pass
                elif line.startswith("data: "):
                    # Only grab the endpoint the FIRST time
                    if not post_url:
                        post_url = line[6:]
                        print(f"Endpoint received: {post_url}")
                        
                        # Send initialize
                        payload = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "clientInfo": {"name": "test", "version": "1.0"},
                                "protocolVersion": "2024-11-05"
                            }
                        }
                        await client.post(f"http://localhost:8000{post_url}", json=payload, headers=headers)
                        print("Sent initialize!")
                    else:
                        # Process other data lines
                        data_str = line[6:]
                        if data_str.startswith("{"):
                            data = json.loads(data_str)
                            print("Received message:", json.dumps(data, indent=2))
                            
                            if data.get("id") == 1:
                                # Send initialized notification
                                payload = {
                                    "jsonrpc": "2.0",
                                    "method": "notifications/initialized"
                                }
                                await client.post(f"http://localhost:8000{post_url}", json=payload, headers=headers)
                                print("Sent initialized notification!")
                                
                                # Now call read_context
                                payload = {
                                    "jsonrpc": "2.0",
                                    "id": 2,
                                    "method": "tools/call",
                                    "params": {
                                        "name": "read_context",
                                        "arguments": {
                                            "chat": "test-1",
                                            "query": "smriti"
                                        }
                                    }
                                }
                                await client.post(f"http://localhost:8000{post_url}", json=payload, headers=headers)
                                print("Sent tools/call!")
                                
                            elif data.get("id") == 2:
                                print("SUCCESS!")
                                break

if __name__ == "__main__":
    asyncio.run(main())
