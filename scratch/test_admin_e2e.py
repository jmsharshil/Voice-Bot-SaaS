import os
import sys
import json
import uuid
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, Role
from conversations.models import SarvamAgent
from agents.models import VoiceAgent
from rest_framework.test import APIRequestFactory, force_authenticate
from accounts.views import UserListView, UserDetailView, login_view, RegisterView
from conversations.views import sarvam_user_agents_api

def run_e2e_tests():
    print("\n=======================================================")
    print("🚀 RUNNING END-TO-END ADMIN MULTI-AGENT ASSIGNMENT TESTS")
    print("=======================================================\n")

    factory = APIRequestFactory()

    # 1. Ensure SuperAdmin
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.create_superuser("admin_e2e", "admin@e2e.com", "adminpass")
    print(f"✅ Admin user ready: {admin.username}")

    # 2. Ensure at least 3 active Sarvam Agents
    s1, _ = SarvamAgent.objects.get_or_create(
        name="Sarvam Counselor AI",
        defaults={"slug": "counselor-ai", "agent_phone": "+917900000001", "is_active": True}
    )
    s2, _ = SarvamAgent.objects.get_or_create(
        name="Sarvam Placement AI",
        defaults={"slug": "placement-ai", "agent_phone": "+917900000002", "is_active": True}
    )
    s3, _ = SarvamAgent.objects.get_or_create(
        name="Sarvam Support AI",
        defaults={"slug": "support-ai", "agent_phone": "+917900000003", "is_active": True}
    )
    all_sarvams = list(SarvamAgent.objects.filter(is_active=True))
    print(f"✅ Active Sarvam Agents in DB: {len(all_sarvams)}")
    for sa in all_sarvams:
        print(f"   - [ID: {sa.id}] {sa.name} ({sa.slug} | {sa.agent_phone})")

    # 3. Create/Ensure Test VoiceAgent
    v_agent = VoiceAgent.objects.first()
    print(f"✅ VoiceAgent available: {v_agent.name if v_agent else 'None'} ({v_agent.id if v_agent else 'None'})")

    # 4. Create a clean test user
    username = f"e2e_client_{uuid.uuid4().hex[:6]}"
    test_user = User.objects.create_user(username=username, email=f"{username}@test.com", password="SecurePassword123!")
    UserProfile.objects.get_or_create(user=test_user)
    print(f"✅ Created fresh test user: {test_user.username} (ID: {test_user.id})")

    # TEST A: Admin assigns multiple Sarvam agents ([s1.id, s2.id]) via UserDetailView PATCH
    print("\n--- TEST A: Assign Multiple Sarvam Agents ([s1, s2]) ---")
    patch_payload = {
        "assigned_sarvam_agent_ids": [s1.id, s2.id]
    }
    if v_agent:
        patch_payload["assigned_agent_id"] = str(v_agent.id)

    req = factory.patch(f"/api/accounts/users/{test_user.id}/", patch_payload, format="json")
    force_authenticate(req, user=admin)
    res = UserDetailView.as_view()(req, pk=test_user.id)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    
    assigned_sarvam_res = res.data.get("profile", {}).get("assigned_sarvam_agents", [])
    print(f"   PATCH Response assigned_sarvam_agents: {assigned_sarvam_res}")
    assert len(assigned_sarvam_res) == 2, f"Expected 2 assigned agents, got {len(assigned_sarvam_res)}"
    assigned_ids = [a["id"] for a in assigned_sarvam_res]
    assert s1.id in assigned_ids and s2.id in assigned_ids
    print("✅ TEST A PASSED: Multiple Sarvam agents assigned successfully via JSON PATCH.")

    # TEST B: Verify GET /api/accounts/users/ returns correct profile badges for the user
    print("\n--- TEST B: Verify UserListView GET ---")
    req = factory.get("/api/accounts/users/")
    force_authenticate(req, user=admin)
    res = UserListView.as_view()(req)
    assert res.status_code == 200
    user_entry = next((u for u in res.data if u["id"] == test_user.id), None)
    assert user_entry is not None
    user_sarvams = user_entry["profile"]["assigned_sarvam_agents"]
    print(f"   UserListView user assigned_sarvam_agents: {user_sarvams}")
    assert len(user_sarvams) == 2
    if v_agent:
        assert str(user_entry["profile"]["assigned_agent_id"]) == str(v_agent.id)
    print("✅ TEST B PASSED: UserListView accurately serializes all assigned bots.")

    # TEST C: Verify /api/sarvam/agents/ returns ONLY the assigned Sarvam agents when called by this user
    print("\n--- TEST C: Verify sarvam_user_agents_api for Assigned User ---")
    req = factory.get("/api/sarvam/agents/")
    force_authenticate(req, user=test_user)
    res = sarvam_user_agents_api(req)
    assert res.status_code == 200
    user_available_sarvams = res.data.get("agents", [])
    print(f"   User accessible Sarvam agents count: {len(user_available_sarvams)}")
    assert len(user_available_sarvams) == 2
    user_avail_ids = [a["id"] for a in user_available_sarvams]
    assert s1.id in user_avail_ids and s2.id in user_avail_ids
    print("✅ TEST C PASSED: sarvam_user_agents_api correctly scopes available agents to user's assigned agents.")

    # TEST D: Update assignment to ALL 3 agents ([s1, s2, s3])
    print("\n--- TEST D: Update Assignment to 3 Sarvam Agents ---")
    patch_payload = {
        "assigned_sarvam_agent_ids": [s1.id, s2.id, s3.id]
    }
    req = factory.patch(f"/api/accounts/users/{test_user.id}/", patch_payload, format="json")
    force_authenticate(req, user=admin)
    res = UserDetailView.as_view()(req, pk=test_user.id)
    assert res.status_code == 200
    assigned_sarvam_res = res.data.get("profile", {}).get("assigned_sarvam_agents", [])
    print(f"   Updated assigned_sarvam_agents: {assigned_sarvam_res}")
    assert len(assigned_sarvam_res) == 3
    print("✅ TEST D PASSED: User can have 3+ agents assigned simultaneously.")

    # TEST E: Register new client with multiple Sarvam agents via RegisterView POST (multipart / form-data)
    print("\n--- TEST E: Register New Client with Multiple Sarvam Agents ---")
    reg_username = f"new_reg_user_{uuid.uuid4().hex[:6]}"
    reg_post_data = {
        "username": reg_username,
        "email": f"{reg_username}@company.com",
        "password": "SuperSecretPass123!",
        "role_name": "Senior Advisor",
        "assigned_sarvam_agent_ids": json.dumps([s1.id, s3.id]),
        "permissions": json.dumps({"can_view_leads": True, "can_view_calls": True})
    }
    if v_agent:
        reg_post_data["assigned_agent_id"] = str(v_agent.id)

    req = factory.post("/api/accounts/register/", reg_post_data, format="multipart")
    force_authenticate(req, user=admin)
    res = RegisterView.as_view()(req)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.data}"
    created_user = User.objects.get(username=reg_username)
    created_sarvams = list(created_user.profile.assigned_sarvam_agents.all())
    print(f"   Newly registered user: {created_user.username}, Assigned Sarvam Agents: {[a.name for a in created_sarvams]}")
    assert len(created_sarvams) == 2
    assert set([a.id for a in created_sarvams]) == set([s1.id, s3.id])
    print("✅ TEST E PASSED: New client created with multiple assigned Sarvam agents.")

    print("\n=======================================================")
    print("🎉 ALL END-TO-END TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================\n")
    return True

if __name__ == "__main__":
    run_e2e_tests()
