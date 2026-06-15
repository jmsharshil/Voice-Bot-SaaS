from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch
import datetime
from agents.models import Industry, AgentRoleTemplate, VoiceAgent
from conversations.models import Conversation
from bot.views import is_within_calling_hours, has_remaining_minutes

class CallingHoursAndQuotaTestCase(TestCase):
    def setUp(self):
        # Create a test agent with required industry and role template
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        industry = Industry.objects.create(name="Healthcare", slug="healthcare")
        role = AgentRoleTemplate.objects.create(
            role_name="Support Template",
            industry=industry,
            system_prompt_template="Prompt",
            default_tone="Neutral",
            default_voice="Voice"
        )
        self.agent = VoiceAgent.objects.create(
            owner=self.user,
            name="Test Bot",
            industry=industry,
            role_template=role,
            minutes_quota=10
        )

    def test_is_within_calling_hours_math(self):
        # Test timezone logic by patching sys.argv to not contain 'test'
        # so it evaluates the actual clock check
        with patch('sys.argv', []):
            # 1. 3:59 AM UTC = 9:29 AM IST (Outside hours)
            time_outside_start = datetime.datetime(2026, 6, 15, 3, 59, tzinfo=datetime.timezone.utc)
            with patch('django.utils.timezone.now', return_value=time_outside_start):
                self.assertFalse(is_within_calling_hours())

            # 2. 4:00 AM UTC = 9:30 AM IST (Exactly start)
            time_start = datetime.datetime(2026, 6, 15, 4, 0, tzinfo=datetime.timezone.utc)
            with patch('django.utils.timezone.now', return_value=time_start):
                self.assertTrue(is_within_calling_hours())

            # 3. 1:00 PM UTC = 6:30 PM IST (Exactly end)
            time_end = datetime.datetime(2026, 6, 15, 13, 0, tzinfo=datetime.timezone.utc)
            with patch('django.utils.timezone.now', return_value=time_end):
                self.assertTrue(is_within_calling_hours())

            # 4. 1:01 PM UTC = 6:31 PM IST (Outside hours)
            time_outside_end = datetime.datetime(2026, 6, 15, 13, 1, tzinfo=datetime.timezone.utc)
            with patch('django.utils.timezone.now', return_value=time_outside_end):
                self.assertFalse(is_within_calling_hours())

    def test_has_remaining_minutes(self):
        # Initial quota is 10, used is 0
        self.assertTrue(has_remaining_minutes(self.agent.id))

        # Add a conversation lasting 9 minutes
        now_time = timezone.now()
        start = now_time - datetime.timedelta(minutes=9)
        c1 = Conversation.objects.create(
            agent=self.agent,
            session_id="session1",
            ended_at=now_time
        )
        Conversation.objects.filter(id=c1.id).update(started_at=start)

        # 9 minutes billed, 1 minute remaining -> True
        self.assertTrue(has_remaining_minutes(self.agent.id))

        # Add a conversation lasting 2 minutes
        start2 = now_time - datetime.timedelta(minutes=2)
        c2 = Conversation.objects.create(
            agent=self.agent,
            session_id="session2",
            ended_at=now_time
        )
        Conversation.objects.filter(id=c2.id).update(started_at=start2)

        # Total billed is now 11 minutes (exceeds quota of 10) -> False
        self.assertFalse(has_remaining_minutes(self.agent.id))
