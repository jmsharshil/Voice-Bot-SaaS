import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
from django.db.models import Count, Q

from .models import ShreyasDepartment, ShreyasUserProfile, ShreyasCallLead
from .classifier import route_and_save_shreyas_lead, classify_caller_interest, format_transcript_to_str

logger = logging.getLogger(__name__)


def get_shreyas_agent_minutes():
    """Fetches minutes allocation & balance for Shreyas Foundation Sarvam Voice Agent."""
    try:
        from conversations.models import SarvamAgent
        agent = SarvamAgent.objects.filter(Q(app_id="Shreyas-fou-5240c43a-8dac") | Q(slug="shreyas-foundation")).first()
        if agent:
            return {
                "allocated_minutes": float(agent.allocated_minutes),
                "remaining_minutes": float(agent.remaining_minutes),
                "used_minutes": float(agent.total_used_minutes),
                "usage_percentage": float(agent.usage_percentage),
            }
    except Exception as e:
        logger.warning(f"Error fetching Shreyas agent minutes: {e}")
    return {
        "allocated_minutes": 5000.0,
        "remaining_minutes": 5000.0,
        "used_minutes": 0.0,
        "usage_percentage": 0.0,
    }


def get_user_profile(user):
    """Retrieves or creates ShreyasUserProfile for the user."""
    if not user.is_authenticated:
        return None
    default_type = "MAIN_ADMIN" if user.is_superuser else "SUB_USER"
    profile, created = ShreyasUserProfile.objects.get_or_create(
        user=user,
        defaults={
            "user_type": default_type,
            "is_master_admin": user.is_superuser
        }
    )
    # Ensure superuser always has MAIN_ADMIN privilege
    if user.is_superuser and profile.user_type != "MAIN_ADMIN":
        profile.user_type = "MAIN_ADMIN"
        profile.is_master_admin = True
        profile.save(update_fields=["user_type", "is_master_admin"])
    return profile


def shreyas_login_view(request):
    """Custom login view for Shreyas Foundation portal."""
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
        if profile and profile.can_view_all_departments():
            return redirect("shreyas-master-dashboard")
        return redirect("shreyas-subuser-dashboard")

    error_msg = None
    if request.method == "POST":
        u = request.POST.get("username", "").strip()
        p = request.POST.get("password", "").strip()
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            profile = get_user_profile(user)
            if profile.can_view_all_departments():
                return redirect("shreyas-master-dashboard")
            return redirect("shreyas-subuser-dashboard")
        else:
            error_msg = "Invalid username or password. Please try again."

    return render(request, "shreyas/login.html", {"error": error_msg})


def shreyas_logout_view(request):
    """Logs out of Shreyas portal."""
    logout(request)
    return redirect("shreyas-login")


@login_required(login_url="/shreyas/login/")
def shreyas_master_dashboard_view(request):
    """
    Main Admin / Main User Dashboard:
    - Main Admin (Superadmin): Can create Main Users and Sub-Users, see all departments.
    - Main User: Created by Main Admin. Can create Sub-Users, see all departments.
    """
    profile = get_user_profile(request.user)
    if not profile.can_view_all_departments():
        return redirect("shreyas-subuser-dashboard")

    departments = ShreyasDepartment.objects.all().order_by("order", "name")

    # Users list:
    # If Main Admin (Superadmin): show all Main Users and Sub-Users
    # If Main User: show Sub-Users
    if profile.is_system_admin:
        managed_users = ShreyasUserProfile.objects.exclude(user=request.user).select_related("user", "created_by").prefetch_related("assigned_departments")
    else:
        managed_users = ShreyasUserProfile.objects.filter(
            Q(created_by=request.user) | Q(user_type="SUB_USER")
        ).exclude(user=request.user).select_related("user", "created_by").prefetch_related("assigned_departments")

    # Metrics
    total_leads = ShreyasCallLead.objects.count()
    hot_leads = ShreyasCallLead.objects.filter(lead_sentiment="HOT").count()
    warm_leads = ShreyasCallLead.objects.filter(lead_sentiment="WARM").count()
    completed_calls = ShreyasCallLead.objects.filter(status="COMPLETED").count()
    callbacks = ShreyasCallLead.objects.filter(pipeline_stage="CALLBACK_SCHEDULED").count()

    context = {
        "user": request.user,
        "profile": profile,
        "departments": departments,
        "managed_users": managed_users,
        "can_create_main_users": profile.can_create_main_users(),
        "can_create_sub_users": profile.can_create_sub_users(),
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "warm_leads": warm_leads,
        "completed_calls": completed_calls,
        "callbacks": callbacks,
        "is_master": True,
        "is_system_admin": profile.is_system_admin,
    }
    context.update(get_shreyas_agent_minutes())
    return render(request, "shreyas/master_dashboard.html", context)


@login_required(login_url="/shreyas/login/")
def shreyas_subuser_dashboard_view(request):
    """
    Sub-User (Department Lead) Dashboard:
    - Strictly scoped to assigned department(s)
    - Zero data leakage from other departments
    """
    profile = get_user_profile(request.user)
    allowed_depts = profile.assigned_departments.filter(is_active=True).order_by("name")

    if profile.can_view_all_departments():
        return redirect("shreyas-master-dashboard")

    if not allowed_depts.exists():
        return render(request, "shreyas/subuser_dashboard.html", {
            "error_unassigned": True,
            "user": request.user,
            "profile": profile,
        })

    primary_dept = allowed_depts.first()
    dept_qs = ShreyasCallLead.objects.filter(department=primary_dept)
    context = {
        "user": request.user,
        "profile": profile,
        "assigned_departments": allowed_depts,
        "current_department": primary_dept,
        "total_leads": dept_qs.count(),
        "hot_leads": dept_qs.filter(lead_sentiment="HOT").count(),
        "warm_leads": dept_qs.filter(lead_sentiment="WARM").count(),
        "completed_calls": dept_qs.filter(status="COMPLETED").count(),
        "callbacks": dept_qs.filter(pipeline_stage="CALLBACK_SCHEDULED").count(),
        "is_master": False,
    }
    context.update(get_shreyas_agent_minutes())
    return render(request, "shreyas/subuser_dashboard.html", context)


# =========================================================================
# JSON API ENDPOINTS (Clean, Fast AJAX for Tables, Modals & Live Updates)
# =========================================================================

@login_required(login_url="/shreyas/login/")
def api_get_leads(request):
    """
    Returns leads in JSON format filtered by department & user access rules.
    """
    profile = get_user_profile(request.user)
    dept_filter = request.GET.get("department", "all")
    sentiment_filter = request.GET.get("sentiment", "all")
    search_q = request.GET.get("search", "").strip()

    qs = ShreyasCallLead.objects.all().select_related("department")

    # Scope permissions
    if not profile.can_view_all_departments():
        allowed_ids = profile.get_allowed_department_ids()
        qs = qs.filter(department_id__in=allowed_ids)
    elif dept_filter and dept_filter != "all":
        if dept_filter == "unassigned":
            qs = qs.filter(department__isnull=True)
        else:
            qs = qs.filter(department__slug=dept_filter)

    if sentiment_filter and sentiment_filter != "all":
        qs = qs.filter(lead_sentiment=sentiment_filter.upper())

    if search_q:
        qs = qs.filter(
            Q(phone_number__icontains=search_q) |
            Q(caller_name__icontains=search_q) |
            Q(transcript__icontains=search_q) |
            Q(summary__icontains=search_q) |
            Q(detected_intent__icontains=search_q)
        )

    leads_data = []
    import urllib.parse
    for l in qs[:150]:
        audio_src = (l.audio_url or "").strip()
        # Fallback to linked SarvamCallRecord audio if lead audio is empty
        if not audio_src and l.sarvam_call_record and l.sarvam_call_record.audio_url:
            audio_src = l.sarvam_call_record.audio_url.strip()
            l.audio_url = audio_src
            l.save(update_fields=["audio_url"])

        # If it's a sarvam.ai or external URL, proxy it so HTML5 audio can play it with credentials
        if audio_src:
            if "sarvam.ai" in audio_src or audio_src.startswith("http"):
                if not audio_src.startswith("/proxy-audio") and not audio_src.startswith("/api/proxy-audio"):
                    audio_src = f"/api/proxy-audio/?url={urllib.parse.quote(audio_src, safe='')}"

        leads_data.append({
            "id": l.id,
            "caller_name": l.caller_name,
            "phone_number": l.phone_number,
            "department_name": l.department.name if l.department else "Unassigned",
            "department_slug": l.department.slug if l.department else "",
            "department_color": l.department.badge_color if l.department else "#64748b",
            "department_icon": l.department.icon if l.department else "fa-tag",
            "duration": l.formatted_duration,
            "status": l.status,
            "sentiment": l.lead_sentiment,
            "pipeline_stage": l.pipeline_stage,
            "audio_url": audio_src,
            "summary": l.summary,
            "transcript": format_transcript_to_str(l.transcript),
            "detected_intent": l.detected_intent,
            "matched_keywords": l.matched_keywords,
            "notes": l.notes,
            "created_at": l.created_at.strftime("%b %d, %Y %I:%M %p"),
        })

    # Calculate stats for the user's accessible scope
    base_qs = ShreyasCallLead.objects.all()
    if not profile.can_view_all_departments():
        base_qs = base_qs.filter(department_id__in=profile.get_allowed_department_ids())

    metrics = {
        "total": base_qs.count(),
        "hot": base_qs.filter(lead_sentiment="HOT").count(),
        "warm": base_qs.filter(lead_sentiment="WARM").count(),
        "completed": base_qs.filter(status="COMPLETED").count(),
        "callbacks": base_qs.filter(pipeline_stage="CALLBACK_SCHEDULED").count(),
    }

    return JsonResponse({
        "status": "success", 
        "leads": leads_data, 
        "metrics": metrics,
        "minutes": get_shreyas_agent_minutes(),
    })


@csrf_exempt
@login_required(login_url="/shreyas/login/")
def api_update_lead(request, lead_id):
    """Updates lead stage or notes."""
    lead = get_object_or_404(ShreyasCallLead, id=lead_id)
    profile = get_user_profile(request.user)

    # Permission check for sub-users
    if not profile.can_view_all_departments():
        if lead.department_id not in profile.get_allowed_department_ids():
            return JsonResponse({"error": "Unauthorized access to this lead"}, status=403)

    data = json.loads(request.body.decode("utf-8") or "{}")
    if "pipeline_stage" in data:
        lead.pipeline_stage = data["pipeline_stage"]
    if "notes" in data:
        lead.notes = data["notes"]
    lead.save()

    return JsonResponse({"status": "success", "message": "Lead updated successfully"})


@csrf_exempt
@login_required(login_url="/shreyas/login/")
def api_manage_department(request):
    """
    Main User only: Add, edit, or toggle department.
    """
    profile = get_user_profile(request.user)
    if not profile.can_view_all_departments():
        return JsonResponse({"error": "Admin permission required"}, status=403)

    data = json.loads(request.body.decode("utf-8") or "{}")
    action = data.get("action", "create")

    if action == "create":
        name = data.get("name", "").strip()
        keywords = data.get("keywords", "").strip()
        color = data.get("badge_color", "#2563eb").strip()
        icon = data.get("icon", "fa-graduation-cap").strip()
        description = data.get("description", "").strip()

        if not name or not keywords:
            return JsonResponse({"error": "Department name and keywords are required"}, status=400)

        slug = slugify(name)
        if ShreyasDepartment.objects.filter(slug=slug).exists():
            return JsonResponse({"error": f"Department with name '{name}' already exists"}, status=400)

        dept = ShreyasDepartment.objects.create(
            name=name,
            slug=slug,
            keywords=keywords,
            badge_color=color,
            icon=icon,
            description=description,
            is_active=True
        )
        return JsonResponse({"status": "success", "message": f"Department '{dept.name}' created successfully!"})

    elif action == "delete":
        dept_id = data.get("id")
        dept = get_object_or_404(ShreyasDepartment, id=dept_id)
        dept_name = dept.name
        dept.delete()
        return JsonResponse({"status": "success", "message": f"Department '{dept_name}' deleted successfully!"})

    elif action == "toggle_active":
        dept_id = data.get("id")
        dept = get_object_or_404(ShreyasDepartment, id=dept_id)
        dept.is_active = not dept.is_active
        dept.save(update_fields=["is_active"])
        return JsonResponse({"status": "success", "is_active": dept.is_active})

    return JsonResponse({"error": "Invalid action"}, status=400)


@csrf_exempt
@login_required(login_url="/shreyas/login/")
def api_manage_subuser(request):
    """
    User Management:
    - Main Admin can create Main Users (who see all depts) and Sub-Users.
    - Main User can create Sub-Users (who see only assigned depts).
    """
    profile = get_user_profile(request.user)
    if not profile.can_create_sub_users():
        return JsonResponse({"error": "Admin permission required"}, status=403)

    data = json.loads(request.body.decode("utf-8") or "{}")
    action = data.get("action", "create")

    if action == "create":
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        email = data.get("email", "").strip()
        role_type = data.get("user_type", "SUB_USER").strip().upper()
        department_ids = data.get("department_ids", [])

        if not username or not password:
            return JsonResponse({"error": "Username and password are required"}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": f"Username '{username}' already exists"}, status=400)

        if role_type == "MAIN_USER":
            if not profile.can_create_main_users():
                return JsonResponse({"error": "Permission denied: Only Main Admin (Superadmin) can create Main Users."}, status=403)
            user = User.objects.create_user(username=username, password=password, email=email)
            ShreyasUserProfile.objects.create(
                user=user,
                user_type="MAIN_USER",
                is_master_admin=True,
                created_by=request.user
            )
            return JsonResponse({"status": "success", "message": f"Main User '{username}' created successfully! They can access all departments and create sub-users."})
        else:
            # Sub-User creation (allowed for Main Admin AND Main User)
            user = User.objects.create_user(username=username, password=password, email=email)
            sub_profile = ShreyasUserProfile.objects.create(
                user=user,
                user_type="SUB_USER",
                is_master_admin=False,
                created_by=request.user
            )
            if department_ids:
                depts = ShreyasDepartment.objects.filter(id__in=department_ids)
                sub_profile.assigned_departments.set(depts)
            return JsonResponse({"status": "success", "message": f"Sub-user '{username}' created successfully and assigned to department!"})

    elif action == "update":
        user_id = data.get("user_id")
        if not user_id:
            return JsonResponse({"error": "User ID is required"}, status=400)
        target_user = get_object_or_404(User, id=user_id)
        if target_user.is_superuser and not profile.is_system_admin:
            return JsonResponse({"error": "Cannot edit superuser"}, status=403)
        target_profile = get_user_profile(target_user)

        # 1. Update Username if changed
        new_username = data.get("username", "").strip()
        if new_username and new_username != target_user.username:
            if User.objects.filter(username=new_username).exclude(id=target_user.id).exists():
                return JsonResponse({"error": f"Username '{new_username}' is already taken"}, status=400)
            target_user.username = new_username

        # 2. Update Password if provided
        new_password = data.get("password", "").strip()
        if new_password:
            target_user.set_password(new_password)

        # 3. Update Email if provided
        if "email" in data:
            target_user.email = data.get("email", "").strip()

        target_user.save()

        # 4. Role Level (only Main Admin can assign MAIN_USER)
        role_type = data.get("user_type", "").strip().upper()
        if role_type:
            if role_type == "MAIN_USER" and not profile.can_create_main_users():
                return JsonResponse({"error": "Permission denied: Only Main Admin can set user to Main User."}, status=403)
            if profile.can_create_main_users():
                target_profile.user_type = role_type
                target_profile.is_master_admin = (role_type == "MAIN_USER")

        # 5. Department Assignment
        if target_profile.user_type == "MAIN_USER":
            target_profile.assigned_departments.clear()
        else:
            dept_ids = data.get("department_ids", [])
            depts = ShreyasDepartment.objects.filter(id__in=dept_ids)
            target_profile.assigned_departments.set(depts)

        target_profile.save()
        return JsonResponse({"status": "success", "message": f"User '{target_user.username}' updated successfully!"})

    elif action == "delete":
        user_id = data.get("user_id")
        target_user = get_object_or_404(User, id=user_id)
        if target_user.is_superuser:
            return JsonResponse({"error": "Cannot delete superuser"}, status=400)
        target_user.delete()
        return JsonResponse({"status": "success", "message": "User deleted successfully"})

    return JsonResponse({"error": "Invalid action"}, status=400)


@csrf_exempt
@login_required(login_url="/shreyas/login/")
def api_create_test_lead(request):
    """
    Allows the user to submit a test call / transcript to verify instant
    and zero-mismatch department routing live on the dashboard.
    """
    data = json.loads(request.body.decode("utf-8") or "{}")
    phone = data.get("phone", "+919876543210").strip()
    name = data.get("name", "Parent / Student").strip()
    transcript = data.get("transcript", "").strip()
    summary = data.get("summary", "").strip()
    duration = float(data.get("duration", 45.0))

    if not transcript:
        return JsonResponse({"error": "Transcript is required for classification test"}, status=400)

    lead = route_and_save_shreyas_lead(
        phone_number=phone,
        caller_name=name,
        transcript=transcript,
        summary=summary,
        duration_seconds=duration,
        status="COMPLETED"
    )

    return JsonResponse({
        "status": "success",
        "message": f"Lead routed successfully to '{lead.department.name if lead.department else 'Unassigned'}'!",
        "department": lead.department.name if lead.department else "Unassigned",
        "matched_keywords": lead.matched_keywords,
        "lead_id": lead.id
    })


@csrf_exempt
@login_required(login_url="/shreyas/login/")
def api_trigger_outbound_call(request):
    """
    Triggers a live outbound call to a customer using the Shreyas Foundation Sarvam Agent.
    """
    from conversations.models import SarvamAgent, SarvamCallRecord
    from conversations.services.kylas_sarvam_bridge import SarvamAgentService

    data = json.loads(request.body.decode("utf-8") or "{}")
    phone = data.get("phone", "").strip()
    name = data.get("name", "Parent / Student").strip()

    if not phone:
        return JsonResponse({"error": "Phone number is required"}, status=400)

    # 1. Resolve Shreyas Sarvam Agent
    sarvam_agent = (
        SarvamAgent.objects.filter(slug="shreyas-foundation", is_active=True).first()
        or SarvamAgent.objects.filter(slug__icontains="shreyas", is_active=True).first()
        or SarvamAgent.objects.filter(name__icontains="shreyas", is_active=True).first()
    )

    if not sarvam_agent:
        return JsonResponse({
            "error": "No Sarvam Agent configured with slug 'shreyas-foundation'. Please add the agent in Django Admin first!"
        }, status=400)

    # 2. Trigger Call via Sarvam API
    res = SarvamAgentService.trigger_outbound_call(
        phone_number=phone,
        customer_name=name,
        sarvam_agent=sarvam_agent
    )

    attempt_id = res.get("attempt_id") if isinstance(res, dict) else None

    # 3. Create initial CallRecord and ShreyasLead
    call_rec = SarvamCallRecord.objects.create(
        sarvam_agent=sarvam_agent,
        attempt_id=attempt_id,
        phone_number=phone,
        candidate_name=name,
        status="DIALING",
        call_type="Outbound Call",
        created_by=request.user
    )

    shreyas_lead = ShreyasCallLead.objects.create(
        sarvam_call_record=call_rec,
        phone_number=phone,
        caller_name=name,
        call_type="Outbound Call",
        status="DIALING",
        interaction_id=attempt_id or f"dial_{call_rec.id}"
    )

    return JsonResponse({
        "status": "success",
        "message": f"Calling {phone} via Sarvam Agent '{sarvam_agent.name}'!",
        "lead_id": shreyas_lead.id,
        "attempt_id": attempt_id
    })


@csrf_exempt
def shreyas_cdr_webhook(request):
    """
    Dedicated webhook endpoint for Shreyas Foundation Sarvam Agent calls.
    Automatically captures completed calls and routes them to the right department.
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = request.POST.dict() or {}

    phone_number = payload.get("user_phone_number") or payload.get("phone_number") or payload.get("phone") or "Unknown"
    caller_name = payload.get("user_name") or payload.get("candidate_name") or "Caller"
    duration = float(payload.get("duration_seconds") or payload.get("call_duration") or 0.0)
    audio_url = payload.get("recording_url") or payload.get("audio_url") or ""
    transcript = payload.get("transcript") or payload.get("conversation_text") or ""
    summary = payload.get("summary") or payload.get("call_summary") or ""
    status = payload.get("call_status") or payload.get("status") or "COMPLETED"
    interaction_id = payload.get("interaction_id") or payload.get("call_id") or ""

    lead = route_and_save_shreyas_lead(
        phone_number=phone_number,
        caller_name=caller_name,
        transcript=transcript,
        summary=summary,
        audio_url=audio_url,
        duration_seconds=duration,
        status=status,
        interaction_id=interaction_id
    )

    return JsonResponse({"status": "received", "lead_id": lead.id, "department": lead.department.name if lead.department else "Unassigned"})
