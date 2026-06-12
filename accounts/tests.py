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

