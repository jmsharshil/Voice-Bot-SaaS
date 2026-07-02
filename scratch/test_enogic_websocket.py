import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Please install websockets first: venv\\Scripts\\pip.exe install websockets")
    sys.exit(1)

async def test_bot(service_num):
    # Zara Agent ID created during setup
    agent_id = "948007ab-6757-4ec8-afdb-b75310e7f01d"
    
    if service_num == 1:
        url = f"ws://localhost:8000/ws/voice-bot/service/?agent_id={agent_id}&language=hi"
    else:
        url = f"ws://localhost:8000/ws/voice-bot/service2/?agent_id={agent_id}&language=hi"
        
    print(f"\n==========================================")
    print(f"Connecting to Enogic ZED Bot (Service {service_num}) at {url}...")
    print(f"==========================================\n")
    
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
            print("\nWaiting for greeting to play (8s)...")
            await asyncio.sleep(8)

            # Step 1: Reply "Haan, business hai" (MSME yes)
            print("\nSending simulated reply: 'Haan, business hai'...")
            payload = {
                "event": "test_text",
                "text": "Haan, business hai"
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(8)

            # Step 2: Reply "Haan, pata hai" (Zed knows yes)
            print("\nSending simulated reply: 'Haan, pata hai'...")
            payload = {
                "event": "test_text",
                "text": "Haan, pata hai"
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(8)

            # Step 3: Reply "Haan purchase karni hai" (Purchase yes)
            print("\nSending simulated reply: 'Haan purchase karni hai'...")
            payload = {
                "event": "test_text",
                "text": "Haan purchase karni hai"
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(8)

            # Cancel receive loop and close
            recv_task.cancel()
            print(f"\nService {service_num} test finished successfully!")

    except Exception as e:
        print(f"Connection failed or encountered error: {e}")

async def main():
    print("Which service do you want to test?")
    print("1. Service 1 (Normal Service)")
    print("2. Service 2 (Service 2)")
    print("3. Both")
    
    # Check if there is pre-defined choice, otherwise ask
    choice = "3"
    print(f"Selecting option {choice} to run test on both services...")
    
    if choice == "1":
        await test_bot(1)
    elif choice == "2":
        await test_bot(2)
    else:
        await test_bot(1)
        await asyncio.sleep(3)
        await test_bot(2)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "1":
            asyncio.run(test_bot(1))
        elif arg == "2":
            asyncio.run(test_bot(2))
        else:
            asyncio.run(main())
    else:
        asyncio.run(main())
