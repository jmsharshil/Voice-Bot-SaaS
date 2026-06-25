from django.urls import re_path
from .consumers import VoiceBotConsumer
from .consumers_service2 import VoiceBotConsumerService2

websocket_urlpatterns = [
    re_path(r'ws/voice-bot/service1/$', VoiceBotConsumer.as_asgi()),
    re_path(r'ws/voice-bot/service2/$', VoiceBotConsumerService2.as_asgi()),
    re_path(r'ws/voice-bot/?', VoiceBotConsumer.as_asgi()),
]