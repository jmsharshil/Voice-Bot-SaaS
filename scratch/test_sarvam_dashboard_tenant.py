import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voice_bot.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from conversations.views import sarvam_leads_page, sarvam_user_agents_api
from accounts.views import login_view
from conversations.models import SarvamAgent

def add_session(request):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request

def run_tests():
    rf = RequestFactory()

    print("\n--- TEST 1: Login API for user 'mahindra' ---")
    mahindra_user = User.objects.get(username="mahindra")
    req_login = rf.post('/api/accounts/login-api/', 
                        data='{"username": "mahindra", "password": "123"}',
                        content_type='application/json')
    req_login = add_session(req_login)
    
    # Authenticate via login_view
    resp_login = login_view(req_login)
    assert resp_login.status_code == 200, f"Login failed: {resp_login.data}"
    print(f"✅ Login successful for mahindra. Assigned agents: {resp_login.data.get('assigned_sarvam_agents')}")
    assert len(resp_login.data.get('assigned_sarvam_agents', [])) == 2, "Expected 2 assigned agents"
    first_slug = resp_login.data['assigned_sarvam_agents'][0]['slug']
    assert first_slug == 'Mahindra-hindi', f"Expected Mahindra-hindi, got {first_slug}"

    print("\n--- TEST 2: sarvam_leads_page root (/sarvam-leads/) for user 'mahindra' ---")
    req_page = rf.get('/sarvam-leads/')
    req_page.user = mahindra_user
    req_page = add_session(req_page)
    resp_page = sarvam_leads_page(req_page)
    assert resp_page.status_code == 302, f"Expected 302 redirect, got {resp_page.status_code}"
    print(f"✅ Root /sarvam-leads/ redirects to: {resp_page.url}")
    assert resp_page.url == '/api/sarvam/Mahindra-hindi/leads/', f"Unexpected redirect URL: {resp_page.url}"

    print("\n--- TEST 3: sarvam_leads_page (/api/sarvam/Mahindra-hindi/leads/) for user 'mahindra' ---")
    req_page2 = rf.get('/api/sarvam/Mahindra-hindi/leads/')
    req_page2.user = mahindra_user
    req_page2 = add_session(req_page2)
    resp_page2 = sarvam_leads_page(req_page2, agent_slug='Mahindra-hindi')
    assert resp_page2.status_code == 200, f"Expected 200 OK, got {resp_page2.status_code}"
    content = resp_page2.content.decode('utf-8')
    assert "Mahindra_car" in content, "Mahindra_car not found in page content"
    assert "Mahindra_pickup" in content, "Mahindra_pickup not found in switcher options"
    print("✅ Dashboard page renders Mahindra_car accurately with switcher options.")

    print("\n--- TEST 4: sarvam_leads_page unauthorized slug (/api/sarvam/Kia/leads/) for user 'mahindra' ---")
    req_page3 = rf.get('/api/sarvam/Kia/leads/')
    req_page3.user = mahindra_user
    req_page3 = add_session(req_page3)
    resp_page3 = sarvam_leads_page(req_page3, agent_slug='Kia')
    assert resp_page3.status_code == 302, f"Expected 302 redirect for unauthorized agent, got {resp_page3.status_code}"
    assert resp_page3.url == '/api/sarvam/Mahindra-hindi/leads/', f"Expected redirect to user's assigned agent, got {resp_page3.url}"
    print("✅ Unauthorized agent request safely redirects to user's primary assigned agent.")

    print("\n--- TEST 5: sarvam_user_agents_api for user 'mahindra' ---")
    from rest_framework.test import APIRequestFactory, force_authenticate
    apirf = APIRequestFactory()
    req_api = apirf.get('/api/sarvam/agents/')
    force_authenticate(req_api, user=mahindra_user)
    resp_api = sarvam_user_agents_api(req_api)
    assert resp_api.status_code == 200, f"Expected 200, got {resp_api.status_code}"
    agents = resp_api.data.get('agents', [])
    agent_names = [a['name'] for a in agents]
    print(f"✅ User agents API returned: {agent_names}")
    assert set(agent_names) == {'Mahindra_car', 'Mahindra_pickup'}, f"Unexpected agents: {agent_names}"

    print("\n--- TEST 6: Testing for user 'kia' ---")
    kia_user = User.objects.get(username="kia")
    req_kia = rf.get('/sarvam-leads/')
    req_kia.user = kia_user
    req_kia = add_session(req_kia)
    resp_kia = sarvam_leads_page(req_kia)
    assert resp_kia.status_code == 302, f"Expected 302 redirect for kia, got {resp_kia.status_code}"
    assert resp_kia.url == '/api/sarvam/Kia/leads/', f"Expected /api/sarvam/Kia/leads/, got {resp_kia.url}"
    print(f"✅ User 'kia' successfully redirects to {resp_kia.url}")

    print("\n🎉 ALL MULTI-TENANT SARVAM DASHBOARD TESTS PASSED SUCCESSFULLY! 🎉\n")

if __name__ == '__main__':
    run_tests()
