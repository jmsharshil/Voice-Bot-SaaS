from django.urls import re_path
from .consumers import VoiceBotConsumer

websocket_urlpatterns = [
    re_path(r'ws/voice-bot/?', VoiceBotConsumer.as_asgi()),
]