from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

class UpdateAgentQuotaTestCase(APITestCase):
    def setUp(self):
        # Create a superuser
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="super@example.com",
            password="superpassword"
        )
        self.client.force_authenticate(user=self.superuser)

        # Create industry and role template
        industry = Industry.objects.create(name="Healthcare", slug="healthcare")
        role = AgentRoleTemplate.objects.create(
            role_name="Support Template",
            industry=industry,
            system_prompt_template="Prompt",
            default_tone="Neutral",
            default_voice="Voice"
        )

        # Create a voice agent
        self.agent = VoiceAgent.objects.create(
            owner=self.superuser,
            name="Aisha Bot",
            industry=industry,
            role_template=role,
            minutes_quota=5000
        )
        self.url = f"/api/agents/{self.agent.id}/update-quota/"

    def test_update_quota_reset_limit(self):
        payload = {
            "minutes_quota": 6000
        }
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.minutes_quota, 6000)

    def test_update_quota_cumulative_addition(self):
        payload = {
            "add_minutes": 3000
        }
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        # 5000 + 3000 = 8000
        self.assertEqual(self.agent.minutes_quota, 8000)

    def test_update_quota_negative_values(self):
        payload = {
            "add_minutes": -500
        }
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
