import asyncio
import websockets

async def test():
    uri = "ws://127.0.0.1:8000/ws/voice-bot/?agent_id=976cc696-c4a5-425d-8a27-060bea71e867"

    async with websockets.connect(uri) as ws:
        print("Connected")
        await asyncio.sleep(60)  # wait for greeting

asyncio.run(test())