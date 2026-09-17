import os
import sys
import django
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voice_bot.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User
from conversations.models import SarvamAgent
from conversations.views import (
    sarvam_user_agents_api,
    sarvam_adjust_agent_minutes_api,
    sarvam_toggle_agent_active_api
)

def run_tests():
    rf = APIRequestFactory()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin_test', 'admin@test.com', 'pass123')

    agent = SarvamAgent.objects.filter(slug='vtech').first()
    if not agent:
        agent = SarvamAgent.objects.create(
            name='vtech',
            slug='vtech',
            agent_phone='+917965853278',
            allocated_minutes=5000.0,
            is_active=True
        )

    print(f"Testing with agent: {agent.name} (id={agent.id}, slug={agent.slug})")

    # Test 1: sarvam_user_agents_api with ?all=true
    req1 = rf.get('/api/sarvam/agents/?all=true')
    force_authenticate(req1, user=admin_user)
    res1 = sarvam_user_agents_api(req1)
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    data1 = res1.data
    assert "agents" in data1
    agent_found = next((a for a in data1["agents"] if a["slug"] == agent.slug), None)
    assert agent_found is not None, "Agent 'vtech' not found in sarvam_user_agents_api"
    assert "is_active" in agent_found, "is_active missing from agent dict"
    assert "allocated_minutes" in agent_found, "allocated_minutes missing"
    assert "used_minutes" in agent_found, "used_minutes missing"
    print(f"✅ Test 1 Passed: sarvam_user_agents_api returned {len(data1['agents'])} agents. Sample: {agent_found}")

    # Test 2: Toggle Active Status
    orig_status = agent.is_active
    req2 = rf.patch(f'/api/sarvam/agents/{agent.id}/toggle/')
    force_authenticate(req2, user=admin_user)
    res2 = sarvam_toggle_agent_active_api(req2, agent_id=agent.id)
    assert res2.status_code == 200
    agent.refresh_from_db()
    assert agent.is_active == (not orig_status), f"Toggle failed: expected {not orig_status}, got {agent.is_active}"
    print(f"✅ Test 2 Passed: Toggled status to {agent.is_active}")

    # Toggle back
    req2_back = rf.patch(f'/api/sarvam/agents/{agent.id}/toggle/')
    force_authenticate(req2_back, user=admin_user)
    sarvam_toggle_agent_active_api(req2_back, agent_id=agent.id)
    agent.refresh_from_db()
    assert agent.is_active == orig_status
    print(f"✅ Restored active status to {agent.is_active}")

    # Test 3: Adjust minutes (SET 5500 and used_minutes override)
    req3 = rf.post(
        f'/api/sarvam/{agent.slug}/adjust-minutes/',
        data=json.dumps({"action": "SET", "minutes": 5500, "used_minutes": 2.5}),
        content_type='application/json'
    )
    force_authenticate(req3, user=admin_user)
    res3 = sarvam_adjust_agent_minutes_api(req3, agent_slug=agent.slug)
    assert res3.status_code == 200, f"Expected 200, got {res3.status_code}: {res3.data}"
    agent.refresh_from_db()
    assert agent.allocated_minutes == 5500.0, f"Expected 5500, got {agent.allocated_minutes}"
    assert agent.total_used_minutes == 2.5, f"Expected used_minutes 2.5, got {agent.total_used_minutes}"
    print(f"✅ Test 3 Passed: Adjusted to SET 5500 mins, used: {agent.total_used_minutes} mins")

    # Test 4: Adjust minutes (ADD 500)
    req4 = rf.post(
        f'/api/sarvam/{agent.slug}/adjust-minutes/',
        data=json.dumps({"action": "ADD", "minutes": 500}),
        content_type='application/json'
    )
    force_authenticate(req4, user=admin_user)
    res4 = sarvam_adjust_agent_minutes_api(req4, agent_slug=agent.slug)
    assert res4.status_code == 200
    agent.refresh_from_db()
    assert agent.allocated_minutes == 6000.0, f"Expected 6000, got {agent.allocated_minutes}"
    print(f"✅ Test 4 Passed: Added 500 mins, now {agent.allocated_minutes} mins")

    # Reset back to 5000 mins and 0 used minutes for clean state
    agent.allocated_minutes = 5000.0
    agent.extra_used_seconds = 0.0
    agent.save()

    print("🎉 All backend integration tests PASSED successfully!")

if __name__ == "__main__":
    run_tests()
