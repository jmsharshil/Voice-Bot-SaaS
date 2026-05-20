import os
import audioop
import math
import struct

def generate_tone_ulaw(filename, frequency=440, duration_sec=2.0, sample_rate=8000):
    num_samples = int(duration_sec * sample_rate)
    pcm_data = []
    for i in range(num_samples):
        value = int(16383 * math.sin(2 * math.pi * frequency * i / sample_rate))
        pcm_data.append(value)
    pcm_bytes = struct.pack('<' + ('h' * len(pcm_data)), *pcm_data)
    ulaw_data = audioop.lin2ulaw(pcm_bytes, 2)
    os.makedirs("mp3_responses", exist_ok=True)
    file_path = os.path.join("mp3_responses", filename)
    with open(file_path, "wb") as f:
        f.write(ulaw_data)
    print(f"✅ Generated: {file_path}")

if __name__ == "__main__":
    print("--- Generating Full Flow Mock Assets ---")
    
    mock_files = [
        ("greeting.raw", 350),           # Intro Tone
        ("test_drive_offer.raw", 440),   # Phase 1 Tone
        ("ask_venue_showroom_home.raw", 554), # Phase 2 Tone
        ("ask_address_time.raw", 659),   # Details Tone
        ("kia_pricing_general.raw", 880),# Global Price Tone
        ("showroom_location.raw", 987)   # Global Location Tone
    ]
    
    for filename, freq in mock_files:
        generate_tone_ulaw(filename, frequency=freq)
        
    print("\nSystem ready for Full Flow Testing!")
