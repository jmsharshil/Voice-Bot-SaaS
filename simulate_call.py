import asyncio
import websockets

async def simulate_call():
    uri = "ws://127.0.0.1:8000/ws/voice-bot/?agent_id=976cc696-c4a5-425d-8a27-060bea71e867"

    async with websockets.connect(uri) as ws:
        print("✅ Connected to VoiceBot")

        with open("ulaw.raw", "rb") as f:
            ulaw_data = f.read()

        # =========================
        # 🎤 SEND SPEECH AUDIO
        # =========================
        for i in range(0, len(ulaw_data), 160):

            if i > 20000:
                print("🛑 Stopping audio (simulate silence)")
                break
            chunk = ulaw_data[i:i+160]

            if len(chunk) < 160:
                chunk = chunk.ljust(160, b'\x00')

            packet = b'\x00' * 12 + chunk  # RTP header + payload
            await ws.send(packet)

            print(f"📤 Sent chunk {i//160}")
            await asyncio.sleep(0.02)  # 20ms pacing

        # =========================
        # 🔇 SEND SILENCE (CRITICAL)
        # =========================
        print("🔇 Sending silence...")

        for _ in range(50):  # 1 second silence
            silence_chunk = b'\x00' * 160
            packet = b'\x00' * 12 + silence_chunk
            await ws.send(packet)
            await asyncio.sleep(0.02)

        # =========================
        # ⏳ WAIT FOR BOT RESPONSE
        # =========================
        print("⏳ Waiting for bot response...")
        await asyncio.sleep(8)   # 🔥 increased time

        print("🔌 Closing connection early (stop sending noise)")
        # await ws.close()
        # wait for bot to finish speaking
        await asyncio.sleep(5)
        print("🎯 Done")


asyncio.run(simulate_call())