import os
import sys
import json
import django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, Role
from conversations.models import SarvamAgent
from agents.models import VoiceAgent
from accounts.serializers import UserSerializer, RegisterSerializer
from rest_framework.test import APIRequestFactory, force_authenticate
from accounts.views import UserListView, UserDetailView

def test_multi_agent_functionality():
    print("=== Testing Sarvam Agents & Multi-Agent Assignment ===")
    
    # Check all active Sarvam agents
    sarvam_agents = list(SarvamAgent.objects.filter(is_active=True))
    print(f"Active Sarvam Agents found: {len(sarvam_agents)}")
    for a in sarvam_agents:
        print(f" - ID: {a.id}, Name: {a.name}, Slug: {a.slug}, Phone: {a.agent_phone}")

    # Ensure at least 2 Sarvam agents exist for testing
    if len(sarvam_agents) < 2:
        a1, _ = SarvamAgent.objects.get_or_create(
            name="Sarvam Counselor",
            defaults={"slug": "sarvam_counselor", "agent_phone": "+918000000001", "is_active": True}
        )
        a2, _ = SarvamAgent.objects.get_or_create(
            name="Sarvam Placement Agent",
            defaults={"slug": "sarvam_placement", "agent_phone": "+918000000002", "is_active": True}
        )
        sarvam_agents = list(SarvamAgent.objects.filter(is_active=True))
        print(f"Created/ensured Sarvam agents: {[a.name for a in sarvam_agents]}")

    # Get or create a test user
    test_user, created = User.objects.get_or_create(username="test_multi_agent_user", defaults={"email": "multi@example.com"})
    if created:
        test_user.set_password("TestPass123!")
        test_user.save()
        UserProfile.objects.get_or_create(user=test_user)
    
    # 1. Test updating via UserSerializer directly with list of IDs
    agent_ids = [a.id for a in sarvam_agents[:2]]
    print(f"\n1. Updating test user with sarvam agent IDs: {agent_ids}")
    serializer = UserSerializer(instance=test_user, data={"assigned_sarvam_agent_ids": agent_ids}, partial=True)
    if serializer.is_valid():
        serializer.save()
        print("✅ UserSerializer.update with list valid and saved.")
    else:
        print(f"❌ UserSerializer errors: {serializer.errors}")
        return False

    # Verify user profile assigned sarvam agents
    test_user.refresh_from_db()
    assigned = list(test_user.profile.assigned_sarvam_agents.all())
    print(f"Assigned Sarvam agents count on user profile: {len(assigned)}")
    assert len(assigned) == len(agent_ids), "Assigned count mismatch!"

    # 2. Test UserDetailView PATCH with JSON
    factory = APIRequestFactory()
    view = UserDetailView.as_view()
    
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser("admin_test", "admin@test.com", "adminpass")

    patch_data = {"assigned_sarvam_agent_ids": [sarvam_agents[0].id]}
    request = factory.patch(f"/api/accounts/users/{test_user.id}/", patch_data, format="json")
    force_authenticate(request, user=admin_user)
    response = view(request, pk=test_user.id)
    print(f"\n2. UserDetailView PATCH JSON status: {response.status_code}")
    print(f"   Response assigned_sarvam_agents: {response.data.get('profile', {}).get('assigned_sarvam_agents')}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # 3. Test UserDetailView PATCH with form-data string format
    form_data = {"assigned_sarvam_agent_ids": json.dumps(agent_ids), "role_name": "Multi Agent Lead"}
    request = factory.patch(f"/api/accounts/users/{test_user.id}/", form_data, format="multipart")
    force_authenticate(request, user=admin_user)
    response = view(request, pk=test_user.id)
    print(f"\n3. UserDetailView PATCH multipart string JSON status: {response.status_code}")
    print(f"   Response assigned_sarvam_agents: {response.data.get('profile', {}).get('assigned_sarvam_agents')}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # 4. Test UserListView GET includes assigned_sarvam_agents
    request = factory.get("/api/accounts/users/")
    force_authenticate(request, user=admin_user)
    response = UserListView.as_view()(request)
    print(f"\n4. UserListView GET status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    found_user = next((u for u in response.data if u["id"] == test_user.id), None)
    assert found_user is not None, "Test user not found in UserListView!"
    print(f"   Found user in list: {found_user['username']}")
    print(f"   Profile assigned_sarvam_agents: {found_user['profile']['assigned_sarvam_agents']}")
    assert len(found_user['profile']['assigned_sarvam_agents']) == len(agent_ids)

    # 5. Test RegisterSerializer with multiple Sarvam agents
    import uuid
    new_username = f"new_sarvam_user_{uuid.uuid4().hex[:6]}"
    reg_data = {
        "username": new_username,
        "email": f"{new_username}@example.com",
        "password": "Password123!",
        "role_name": "Counselor Lead",
        "assigned_sarvam_agent_ids": agent_ids
    }
    reg_serializer = RegisterSerializer(data=reg_data)
    assert reg_serializer.is_valid(), f"RegisterSerializer errors: {reg_serializer.errors}"
    new_user = reg_serializer.save()
    new_assigned = list(new_user.profile.assigned_sarvam_agents.all())
    print(f"\n5. RegisterSerializer created user {new_username} with {len(new_assigned)} Sarvam agents.")
    assert len(new_assigned) == len(agent_ids), "RegisterSerializer assigned agents mismatch!"

    print("\n🎉 ALL BACKEND TESTS (UPDATE + REGISTER) PASSED SUCCESSFULLY!")
    return True

if __name__ == "__main__":
    test_multi_agent_functionality()
