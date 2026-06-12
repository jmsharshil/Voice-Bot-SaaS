import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Please install websockets first: venv\\Scripts\\pip.exe install websockets")
    sys.exit(1)

async def test_bot():
    agent_id = "8110149e-2c74-47e0-b7b5-f20b884fc0c9"
    url = f"ws://localhost:8001/ws/voice-bot/?agent_id={agent_id}&language=hi"
    
    print(f"Connecting to Voice Bot WebSocket at {url}...")
    try:
        async with websockets.connect(url) as websocket:
            print("Connected successfully!")
            
            # Helper task to print incoming media/text events
            async def receive_messages():
                media_count = 0
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        event = data.get("event")
                        if event == "media":
                            media_count += 1
                            if media_count % 50 == 0:
                                print(f"  [AUDIO]: Received {media_count} audio frames...")
                        else:
                            print(f"<- [EVENT RECEIVED]: {data}")
                except Exception as e:
                    print(f"Receive loop error: {e}")

            # Start receive loop in background
            recv_task = asyncio.create_task(receive_messages())

            # Wait a few seconds for the greeting to finish streaming
            print("\nWaiting for greeting to play (15s)...")
            await asyncio.sleep(15)

            # Step 1: Reply "Haan boliye" to greeting
            print("\nSending simulated reply: 'Haan boliye'...")
            payload = {
                "event": "test_text",
                "text": "Haan boliye"
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(12)

            # Step 2: Reply "city drives ke liye" to discovery question
            print("\nSending simulated reply: 'city drives ke liye'...")
            payload = {
                "event": "test_text",
                "text": "city drives ke liye"
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(12)

            # Step 3: Reply "10 se 15 lakh ka budget" to budget question
            print("\nSending simulated reply: '10 se 15 lakh ka budget'...")
            payload = {
                "event": "test_text",
                "text": "10 se 15 lakh ka budget"
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(12)

            # Cancel receive loop and close
            recv_task.cancel()
            print("\nTest finished successfully!")

    except Exception as e:
        print(f"Connection failed or encountered error: {e}")

if __name__ == "__main__":
    asyncio.run(test_bot())
