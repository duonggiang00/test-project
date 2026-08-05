import requests
import json
import httpx
import asyncio

async def run_chat_test():
    url = "http://127.0.0.1:8000/ai/chat"
    payload = {
        "messages": [
            {"role": "user", "content": "Hello, who are you?"}
        ]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            print("Status:", response.status_code)
            async for chunk in response.aiter_text():
                print(chunk, end="")

if __name__ == "__main__":
    asyncio.run(run_chat_test())
