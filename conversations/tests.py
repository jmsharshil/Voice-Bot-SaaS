from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from agents.models import VoiceAgent, Industry
from conversations.models import Conversation
from conversations.views import _round_seconds_to_billed_minutes, _calculate_bot_usage
from django.contrib.auth.models import User
from django.db import models

class MinutesTrackingTestCase(TestCase):
    def setUp(self):
        # Create user & agent
        self.user = User.objects.create_user(username="testadmin", password="password")
        self.industry = Industry.objects.create(name="Automotive", slug="automotive")
        self.agent = VoiceAgent.objects.create(
            owner=self.user,
            name="Test Bot",
            industry=self.industry,
            minutes_quota=5000
        )

    def test_rounding_logic(self):
        # 0 seconds -> 0.0
        self.assertEqual(_round_seconds_to_billed_minutes(0), 0.0)
        self.assertEqual(_round_seconds_to_billed_minutes(-5), 0.0)
        
        # 1-29 seconds -> 0.5
        self.assertEqual(_round_seconds_to_billed_minutes(1), 0.5)
        self.assertEqual(_round_seconds_to_billed_minutes(15), 0.5)
        self.assertEqual(_round_seconds_to_billed_minutes(29), 0.5)
        
        # 30-59 seconds -> 1.0
        self.assertEqual(_round_seconds_to_billed_minutes(30), 1.0)
        self.assertEqual(_round_seconds_to_billed_minutes(45), 1.0)
        self.assertEqual(_round_seconds_to_billed_minutes(59), 1.0)
        
        # 60-89 seconds -> 1.5
        self.assertEqual(_round_seconds_to_billed_minutes(60), 1.5)
        self.assertEqual(_round_seconds_to_billed_minutes(75), 1.5)
        self.assertEqual(_round_seconds_to_billed_minutes(89), 1.5)
        
        # 90-119 seconds -> 2.0
        self.assertEqual(_round_seconds_to_billed_minutes(90), 2.0)
        self.assertEqual(_round_seconds_to_billed_minutes(119), 2.0)

        # 122 seconds (2m 2s) -> 122 -> 150 seconds -> 2.5 minutes
        self.assertEqual(_round_seconds_to_billed_minutes(122), 2.5)

    def test_bot_usage_aggregation(self):
        # Create some conversation records
        now = timezone.now()
        
        # Conv 1: 15 seconds (billed 0.5m)
        Conversation.objects.create(
            agent=self.agent,
            session_id="session_1",
            started_at=now,
            ended_at=now + timedelta(seconds=15)
        )
        
        # Conv 2: 45 seconds (billed 1.0m)
        Conversation.objects.create(
            agent=self.agent,
            session_id="session_2",
            started_at=now,
            ended_at=now + timedelta(seconds=45)
        )
        
        # Conv 3: 122 seconds (billed 2.5m)
        Conversation.objects.create(
            agent=self.agent,
            session_id="session_3",
            started_at=now,
            ended_at=now + timedelta(seconds=122)
        )

        # Conv 4: Active/incomplete (no ended_at, should not count)
        Conversation.objects.create(
            agent=self.agent,
            session_id="session_4",
            started_at=now,
            ended_at=None
        )

        # Total expected: 0.5 + 1.0 + 2.5 = 4.0 minutes
        total_usage = _calculate_bot_usage(self.agent)
        self.assertEqual(total_usage, 4.0)

