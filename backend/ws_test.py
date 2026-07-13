import asyncio
import websockets

async def test():
    uri = "ws://localhost:8000/ws/call_does_not_exist/test-id?channel=phone"
    print(f"Connecting to {uri}")
    try:
        async with websockets.connect(uri, origin="http://localhost:8000") as ws:
            print("Connected!")
            while True:
                msg = await ws.recv()
                print("Received:", msg)
    except Exception as e:
        print("Error:", type(e), e)

asyncio.run(test())
