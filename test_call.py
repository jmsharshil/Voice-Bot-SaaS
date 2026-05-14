import asyncio
import websockets
import json

async def test_call():
    # Using localhost for testing to avoid ngrok 502 errors
    uri = "ws://localhost:8000/ws/voice-bot/?agent_id=5ceea0c9-f64e-4bde-ba72-3b0777b791d8&from=+919909466119"
    
    print(f"🚀 Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            # 1. Send the 'start' event with a test streamSid
            start_msg = {
                "event": "start",
                "start": {
                    "streamSid": "STREAM_TEST_007",
                    "customParameters": {"callerNumber": "+919909466119"}
                }
            }
            await websocket.send(json.dumps(start_msg))
            print("✅ Sent 'start' event with streamSid: STREAM_TEST_007")
            
            # Keep connection open for 2 seconds to ensure DB save
            await asyncio.sleep(2)
            print("🏁 Test finished. Check your server logs!")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_call())
