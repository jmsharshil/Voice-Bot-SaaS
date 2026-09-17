from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import Role, UserProfile

class LoginAPITestCase(APITestCase):
    def setUp(self):
        # Create a superuser (will trigger the fixed bug if bug exists)
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="super@example.com",
            password="superpassword"
        )
        
        # Create a role
        self.role = Role.objects.create(
            name="Client Admin",
            permissions={"is_admin": True, "can_manage_users": True}
        )

        # Create a regular user
        self.regular_user = User.objects.create_user(
            username="normaluser",
            email="normal@example.com",
            password="normalpassword"
        )
        
        # Assign role to user profile
        self.regular_user.profile.role = self.role
        self.regular_user.profile.save()

        self.login_url = "/api/accounts/login-api/"

    def test_superuser_login_success(self):
        payload = {
            "username": "superadmin",
            "password": "superpassword"
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["username"], "superadmin")
        self.assertTrue(response.data["is_superuser"])
        self.assertTrue(response.data["permissions"].get("is_admin"))

    def test_regular_user_login_success(self):
        payload = {
            "username": "normaluser",
            "password": "normalpassword"
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["username"], "normaluser")
        self.assertEqual(response.data["role"], "Client Admin")
        self.assertTrue(response.data["permissions"].get("is_admin"))

    def test_incorrect_password(self):
        payload = {
            "username": "superadmin",
            "password": "wrongpassword"
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["code"], "wrong_password")

    def test_user_not_found(self):
        payload = {
            "username": "nonexistent",
            "password": "somepassword"
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "user_not_found")


class RegisterAPITestCase(APITestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="super@example.com",
            password="superpassword"
        )
        self.client.force_authenticate(user=self.superuser)
        self.register_url = "/api/accounts/register/"

    def test_register_client_multipart(self):
        payload = {
            "username": "newclient",
            "email": "new@client.com",
            "password": "clientpassword",
            "role_name": "My Custom Role",
            "permissions": '{"is_admin": true, "can_view_leads": true}'
        }
        response = self.client.post(self.register_url, payload, format="multipart")
        print("RESPONSE STATUS:", response.status_code)
        print("RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_client_with_can_manage_team(self):
        payload = {
            "username": "clientwithteam",
            "email": "team@client.com",
            "password": "clientpassword",
            "role_name": "Team Administrator Role",
            "permissions": '{"is_admin": false, "can_view_leads": true, "can_manage_team": true}'
        }
        response = self.client.post(self.register_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(username="clientwithteam")
        self.assertTrue(new_user.profile.custom_permissions.get("can_manage_team"))
        self.assertTrue(new_user.profile.custom_permissions.get("can_view_leads"))

    def test_team_member_management_can_manage_team(self):
        from agents.models import VoiceAgent, Industry, AgentRoleTemplate
        industry = Industry.objects.create(name="Support", slug="support")
        role = AgentRoleTemplate.objects.create(
            role_name="Support Template",
            industry=industry,
            system_prompt_template="Prompt",
            default_tone="Neutral",
            default_voice="Voice"
        )
        agent = VoiceAgent.objects.create(
            name="Support Bot",
            industry=industry,
            role_template=role,
            owner=self.superuser,
            minutes_quota=1000,
            is_active=True
        )

        client_user = User.objects.create_user(username="client_admin", password="password")
        client_user.profile.assigned_agent = agent
        client_user.profile.custom_permissions = {"can_manage_team": True}
        client_user.profile.save()

        # Auth as client_admin to manage team
        self.client.force_authenticate(user=client_user)

        # 1. Create a team member with can_manage_team: true
        payload = {
            "username": "sub_team_admin",
            "email": "sub@team.com",
            "password": "password123",
            "permissions": {
                "can_view_leads": True,
                "can_manage_team": True
            }
        }
        response = self.client.post("/api/accounts/team/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sub_user = User.objects.get(username="sub_team_admin")
        self.assertTrue(sub_user.profile.custom_permissions.get("can_manage_team"))

        # 2. Update the team member to disable can_manage_team
        update_payload = {
            "permissions": {
                "can_view_leads": True,
                "can_manage_team": False
            }
        }
        response = self.client.put(f"/api/accounts/team/{sub_user.id}/", update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sub_user.refresh_from_db()
        self.assertFalse(sub_user.profile.custom_permissions.get("can_manage_team"))

    def test_company_logo_recursive_resolution(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 1. Setup Creator Client
        creator = User.objects.create_user(username="creator_client", password="password")
        logo_file = SimpleUploadedFile("logo.png", b"file_content", content_type="image/png")
        creator.profile.company_logo = logo_file
        creator.profile.save()

        # 2. Setup Sub User created by Creator
        sub_user = User.objects.create_user(username="sub_user", password="password")
        sub_user.profile.created_by = creator
        sub_user.profile.save()

        # 3. Verify that sub_user resolves the creator's logo
        resolved_logo = sub_user.profile.get_company_logo()
        self.assertIsNotNone(resolved_logo)
        self.assertEqual(resolved_logo.name, creator.profile.company_logo.name)


class MinutesUsageAPITestCase(APITestCase):
    def setUp(self):
        from agents.models import VoiceAgent, Industry, AgentRoleTemplate
        self.industry = Industry.objects.create(name="Tech", slug="tech")
        self.role = AgentRoleTemplate.objects.create(
            role_name="Bot Agent",
            industry=self.industry,
            description="Desc",
            system_prompt_template="Hello {agent_name}",
            default_tone="Neutral",
            default_voice="Voice"
        )
        
        self.superuser = User.objects.create_superuser(
            username="superadmin", email="super@example.com", password="superpassword"
        )
        self.client_user = User.objects.create_user(
            username="client_user", password="password"
        )
        self.agent = VoiceAgent.objects.create(
            name="Aisha Bot",
            industry=self.industry,
            role_template=self.role,
            owner=self.superuser,
            minutes_quota=1000,
            is_active=True
        )
        self.client_user.profile.assigned_agent = self.agent
        self.client_user.profile.save()

    def test_minutes_usage_superadmin(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/api/minutes-usage/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_admin"])
        self.assertEqual(len(response.data["bots"]), 1)
        self.assertEqual(response.data["bots"][0]["bot_name"], "Aisha Bot")

    def test_minutes_usage_client(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get("/api/minutes-usage/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_admin"])
        self.assertEqual(response.data["bot_name"], "Aisha Bot")
        self.assertEqual(response.data["quota_minutes"], 1000)
        self.assertEqual(response.data["used_minutes"], 0.0)
        self.assertEqual(response.data["remaining_minutes"], 1000.0)

