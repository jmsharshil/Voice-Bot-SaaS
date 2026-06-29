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


from conversations.views import get_campaign_lead_conversation
from bot.models import Campaign
from rest_framework.test import APIRequestFactory, force_authenticate

class CampaignLeadConversationTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="testadmin2", password="password")
        self.industry = Industry.objects.create(name="Automotive", slug="automotive-test")
        self.agent = VoiceAgent.objects.create(
            owner=self.user,
            name="Test Bot 2",
            industry=self.industry,
            minutes_quota=5000
        )
        # Create campaigns
        self.campaign_1 = Campaign.objects.create(
            name="Campaign 1",
            agent=self.agent,
            ended_at=timezone.now() - timedelta(days=2) + timedelta(hours=1)
        )
        Campaign.objects.filter(id=self.campaign_1.id).update(started_at=timezone.now() - timedelta(days=2))
        self.campaign_1.refresh_from_db()

        self.campaign_2 = Campaign.objects.create(
            name="Campaign 2",
            agent=self.agent,
            ended_at=None
        )
        Campaign.objects.filter(id=self.campaign_2.id).update(started_at=timezone.now())
        self.campaign_2.refresh_from_db()

        # Create conversations
        # 1. Answered call in campaign 1 (from 2 days ago)
        self.conv_1 = Conversation.objects.create(
            agent=self.agent,
            campaign_id=self.campaign_1.id,
            session_id="session_c1_ans",
            user_number="9104142402",
            ended_at=self.campaign_1.started_at + timedelta(minutes=6)
        )
        Conversation.objects.filter(id=self.conv_1.id).update(started_at=self.campaign_1.started_at + timedelta(minutes=5))
        self.conv_1.refresh_from_db()

        # 2. Inbound/Manual call (campaign_id is None) from 1 day ago
        self.conv_manual = Conversation.objects.create(
            agent=self.agent,
            campaign_id=None,
            session_id="session_manual",
            user_number="9104142402",
            ended_at=timezone.now() - timedelta(days=1) + timedelta(minutes=2)
        )
        Conversation.objects.filter(id=self.conv_manual.id).update(started_at=timezone.now() - timedelta(days=1))
        self.conv_manual.refresh_from_db()

    def test_get_campaign_lead_conversation_success(self):
        # Retrieve answered call for campaign 1
        request = self.factory.get(
            f"/api/conversations/campaign-lead/?campaign_id={self.campaign_1.id}&phone=9104142402"
        )
        force_authenticate(request, user=self.user)
        response = get_campaign_lead_conversation(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_id"], "session_c1_ans")

    def test_get_campaign_lead_conversation_missed_no_fallback_to_other_campaign(self):
        # Retrieve call for campaign 2 (where they missed call, so self.campaign_2.id has no conversation)
        request = self.factory.get(
            f"/api/conversations/campaign-lead/?campaign_id={self.campaign_2.id}&phone=9104142402"
        )
        force_authenticate(request, user=self.user)
        response = get_campaign_lead_conversation(request)
        # Should return 404 since the user didn't pick up in campaign 2 (we should not fall back to campaign 1 conversation)
        self.assertEqual(response.status_code, 404)


