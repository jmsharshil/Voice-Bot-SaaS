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