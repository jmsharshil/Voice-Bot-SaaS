from django.core.management.base import BaseCommand
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

from .stt import listen
from .tts import speak

class Command(BaseCommand):
    help = "Terminal voice chat using Azure (STT + GPT + TTS)"

    def handle(self, *args, **options):

        # Load .env
        ROOT = Path(__file__).resolve().parents[3]
        load_dotenv(ROOT / ".env")

        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )

        DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        speak("Voice agent is ready. Speak now.")

        while True:
            try:
                user_text = listen()

                if not user_text:
                    continue

                if user_text.lower() in {"exit", "quit", "stop"}:
                    speak("Goodbye.")
                    break

                response = client.chat.completions.create(
                    model=DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": "You are a helpful voice assistant"},
                        {"role": "user", "content": user_text},
                    ],
                )

                reply = response.choices[0].message.content.strip()
                speak(reply)

            except Exception as e:
                self.stderr.write(str(e))