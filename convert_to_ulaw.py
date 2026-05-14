import wave
import audioop

def wav_to_ulaw(input_file, output_file):
    with wave.open(input_file, 'rb') as wav:
        pcm_data = wav.readframes(wav.getnframes())

        # Convert PCM → µ-law
        ulaw = audioop.lin2ulaw(pcm_data, 2)

        print("ULAW length:", len(ulaw))

        with open(output_file, "wb") as f:
            f.write(ulaw)

        print("✅ Saved:", output_file)


# 🔥 RUN
wav_to_ulaw("test.wav", "ulaw.raw")