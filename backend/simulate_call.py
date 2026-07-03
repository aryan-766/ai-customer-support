import asyncio
import httpx
import websockets
import json

from app.core.tts.factory import TTSFactory

async def simulate():
    print("Waiting 10 seconds for browser subagent to load...")
    await asyncio.sleep(10)
    print("Starting simulated call...")
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/api/v1/calls/start", json={"channel": "phone"})
        data = res.json()
        ws_url = data["ws_url"]
        call_id = data["call_id"]
        
    print(f"Call started: {call_id}")
    print("Go to the frontend dashboard to view live transcript: http://localhost:3000/calls/" + call_id)
    
    # Synthesize test audio
    tts = TTSFactory.get_provider()
    
    async with websockets.connect(ws_url) as ws:
        print("Connected to WS. Waiting for greeting...")
        # Receive greeting
        async for msg in ws:
            if isinstance(msg, bytes):
                pass
            else:
                event = json.loads(msg)
                print("WS EVENT:", event)
                if event.get("type") == "agent_response":
                    break
                    
        await asyncio.sleep(2)
        
        print("Sending simulated customer speech...")
        # Synthesize "My powerbank is not charging, what should I do?"
        async for chunk in tts.synthesize_stream("My powerbank is not charging, what should I do?"):
            await ws.send(chunk)
            await asyncio.sleep(0.01)
            
        print("Waiting for AI response...")
        async for msg in ws:
            if not isinstance(msg, bytes):
                event = json.loads(msg)
                print("WS EVENT:", event)
                if event.get("type") == "agent_response":
                    break
                    
        await asyncio.sleep(2)
        print("Ending call...")

if __name__ == "__main__":
    asyncio.run(simulate())
