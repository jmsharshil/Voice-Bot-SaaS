"""
ASGI config for voice_bot project.
"""

import os
import sys
import codecs

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Prevent Windows console encoding errors with emojis/non-ASCII chars
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

django_asgi_app = get_asgi_application()

# Mute noisy network/HTTP loggers globally at startup
import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# Load and cache all intent matchers in a background thread to prevent Azure startup timeouts
def prewarm_matchers_in_background():
    import time
    time.sleep(2)  # Give Daphne a moment to bind and start listening
    try:
        from conversations.consumers import get_matcher as get_matcher_1
        from conversations.consumers_service2 import get_matcher as get_matcher_2
        
        print("🚀 [STARTUP-BG]: Background pre-loading and embedding all intent matchers...")
        for get_m in [get_matcher_1, get_matcher_2]:
            get_m("AUTOMOBILE_MATCHER", "automobile_intents.json")
            get_m("NAAVYA_MATCHER", "automobile_bot/data/Naavya_intents.json")
            get_m("LOAN_MATCHER", "loan_bot/data/loan_intents.json")
            get_m("REMINDER_MATCHER", "reminder_bot/data/reminder_intents.json")
            get_m("TEMP_REAL_ESTATE_MATCHER", "temp_real_estate_bot/data/real_estate_intents.json")
            get_m("ENOGIC_MATCHER", "enogic_bot/data/enogic_intents.json")
            get_m("SAMSUNG_MATCHER", "samsung_bot/data/samsung_intents.json")
        print("✅ [STARTUP-BG]: All intent matchers successfully pre-loaded and embedded in memory!")
    except Exception as e:
        print(f"⚠️ [STARTUP-BG WARNING]: Failed to pre-load matchers: {e}")

import threading
threading.Thread(target=prewarm_matchers_in_background, daemon=True).start()

import conversations.routing  # import AFTER Django setup

from channels.generic.websocket import WebsocketConsumer

class _RejectUnknownPaths:
    """Silently close WebSocket connections to unregistered paths."""
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        try:
            await self.inner(scope, receive, send)
        except ValueError as e:
            if "No route found" in str(e):
                # Unknown path — close the connection cleanly, no traceback
                await send({"type": "websocket.close", "code": 4004})
            else:
                raise

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": _RejectUnknownPaths(
        AuthMiddlewareStack(
            URLRouter(
                conversations.routing.websocket_urlpatterns
            )
        )
    ),
})


# """
# ASGI config for voice_bot project.
# """

# import os

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")

# # Must be called first — triggers Django's app registry setup
# from django.core.asgi import get_asgi_application
# django_asgi_app = get_asgi_application()

# # Import channels and routing AFTER Django is initialised
# # Importing before get_asgi_application() risks AppRegistryNotReady errors
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import conversations.routing

# application = ProtocolTypeRouter({
#     "http": django_asgi_app,

#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             conversations.routing.websocket_urlpatterns
#         )
#     ),
# })