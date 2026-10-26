"""
AI Dashboard Copilot Service
=============================
Provides intelligent natural language analytics and query resolution
for the VoiceBot SaaS Dashboard using Azure OpenAI Function Calling.

Capabilities:
- Live call counts, inbound/outbound split for ANY date, day, month, or timeframe
- Strict dashboard-scoped isolation (queries ONLY the active agent dashboard)
- Accurate lead metrics (Hot, Warm, Cold, Callbacks, Not Interested)
- Detailed lead lists with customer names, phone numbers, and topics
- Exact call logs with call directions, campaigns, timestamps, and customer interests
- Multi-tenant tenant-isolation (users only query their own bot data)
"""

import json
import logging
import re
import calendar
from datetime import datetime, timedelta, timezone as py_tz
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.conf import settings

from openai import AzureOpenAI

logger = logging.getLogger(__name__)

# Initialize Azure OpenAI Client
_azure_client = None

def get_azure_client():
    global _azure_client
    if _azure_client is None:
        _azure_client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    return _azure_client


MONTH_MAP = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}


# =====================================================================
# =====================================================================
# TIME FILTER HELPER (EXACT DAY, MONTH & TIMEFRAME PARSER - IST AWARE)
# =====================================================================

def parse_timeframe(timeframe_str, now=None):
    """
    Parses natural language timeframe string into an exact (start_dt, end_dt, label) tuple.
    Handles:
    - Single days: '17 oct', '17 october', 'oct 17', 'october 17 2026', 'today', 'yesterday'
    - Entire months: 'september', 'in september 2026', 'this month', 'last month'
    - Weeks: 'this week', 'last week', 'past 7 days'
    - 'all', 'total' -> None, None, 'All Time'
    Uses India Standard Time (Asia/Kolkata) for accurate boundary calculation.
    """
    if not now:
        now = timezone.localtime(timezone.now())
    tz = now.tzinfo or timezone.get_current_timezone()

    tf = str(timeframe_str or 'all').lower().strip()

    # 1. Today
    if tf in ['today', 'aaj']:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, 'Today'

    # 2. Yesterday
    if tf in ['yesterday', 'kal']:
        yest = now - timedelta(days=1)
        start = yest.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yest.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, 'Yesterday'

    # 3. Check for specific day + month: e.g. '17 oct', '17th october', 'oct 17', 'october 17 2026'
    for m_name, m_num in MONTH_MAP.items():
        # Case A: '17 oct' or '17th october'
        pattern_a = r'(\b\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?\b' + m_name + r'\b'
        match_a = re.search(pattern_a, tf)
        if match_a:
            day = int(match_a.group(1))
            yr_match = re.search(r'\b(202\d)\b', tf)
            yr = int(yr_match.group(1)) if yr_match else now.year
            start = datetime(yr, m_num, day, 0, 0, 0, tzinfo=tz)
            end = datetime(yr, m_num, day, 23, 59, 59, 999999, tzinfo=tz)
            return start, end, start.strftime('%d %B %Y')

        # Case B: 'oct 17' or 'october 17th'
        pattern_b = r'\b' + m_name + r'\b\s*(\d{1,2})(?:st|nd|rd|th)?\b'
        match_b = re.search(pattern_b, tf)
        if match_b:
            day = int(match_b.group(1))
            yr_match = re.search(r'\b(202\d)\b', tf)
            yr = int(yr_match.group(1)) if yr_match else now.year
            start = datetime(yr, m_num, day, 0, 0, 0, tzinfo=tz)
            end = datetime(yr, m_num, day, 23, 59, 59, 999999, tzinfo=tz)
            return start, end, start.strftime('%d %B %Y')

    # 4. This week / Last 7 days
    if tf in ['this_week', 'this week', 'week', 'current_week']:
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now, 'This Week'

    if tf in ['last_week', 'last week', 'past_week']:
        last_week_end = (now - timedelta(days=now.weekday() + 1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        last_week_start = (last_week_end - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        return last_week_start, last_week_end, 'Last Week'

    if tf in ['last_7_days', 'last 7 days', '7days', '7_days']:
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now, 'Past 7 Days'

    # 5. This month / Last 30 days
    if tf in ['this_month', 'this month', 'current_month']:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now, 'This Month'

    if tf in ['last_month', 'last month']:
        first_this_month = now.replace(day=1)
        last_day_prev_month = first_this_month - timedelta(days=1)
        start = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = last_day_prev_month.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end, start.strftime('%B %Y')

    if tf in ['last_30_days', 'last 30 days', '30days']:
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now, 'Past 30 Days'

    # 6. Entire Named Month (e.g. 'september', 'in september 2026', 'october')
    for m_name, m_num in MONTH_MAP.items():
        if re.search(r'\b' + m_name + r'\b', tf):
            yr_match = re.search(r'\b(202\d)\b', tf)
            yr = int(yr_match.group(1)) if yr_match else now.year
            _, last_day = calendar.monthrange(yr, m_num)
            start = datetime(yr, m_num, 1, 0, 0, 0, tzinfo=tz)
            end = datetime(yr, m_num, last_day, 23, 59, 59, 999999, tzinfo=tz)
            return start, end, datetime(yr, m_num, 1).strftime('%B %Y')

    # 7. Specific single ISO date (e.g. 2026-10-06)
    iso_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', tf)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        start = datetime(y, m, d, 0, 0, 0, tzinfo=tz)
        end = datetime(y, m, d, 23, 59, 59, 999999, tzinfo=tz)
        return start, end, start.strftime('%d %B %Y')

    return None, None, 'All Time'


# =====================================================================
# DASHBOARD-SCOPED QUERY HELPER
# =====================================================================

def get_scoped_records(user, timeframe="all", current_agent_slug=None, agent_name=None):
    """
    Returns filtered QuerySet of SarvamCallRecord scoped to user, timeframe, and active dashboard agent.
    Filters on created_at (call trigger timestamp).
    Enforces multi-tenant sub-user scoping: sub-users only see data for their main owner's assigned agent.
    """
    from conversations.models import SarvamCallRecord, SarvamAgent

    qs = SarvamCallRecord.objects.all()

    # User / Sub-user access control scoping
    if user and not getattr(user, 'is_superuser', False):
        from conversations.views import _get_user_allowed_sarvam_agents
        is_su, allowed_agents = _get_user_allowed_sarvam_agents(user)
        if not is_su:
            qs = qs.filter(sarvam_agent__in=allowed_agents)

        # Personal activity scoping for sub-users
        user_prof = getattr(user, 'profile', None)
        user_p = getattr(user_prof, 'custom_permissions', {}) if user_prof else {}
        is_subuser = bool(
            user.is_authenticated and
            user_prof and user_prof.created_by and
            not user_p.get("is_admin") and
            not user_p.get("can_manage_team")
        )
        if is_subuser:
            raw_st = user_p.get("assigned_stores", [])
            if isinstance(raw_st, str) and raw_st.strip():
                assigned_st_list = [s.strip().lower() for s in raw_st.split(",") if s.strip()]
            elif isinstance(raw_st, list) and raw_st:
                assigned_st_list = [str(s).strip().lower() for s in raw_st if str(s).strip()]
            else:
                assigned_st_list = []

            # STRICT SUB-USER PERSONAL SCOPING (matches views.py line 3528):
            # Sub-user can strictly see ONLY their own personal activity: calls they triggered, their campaigns, or assigned stores.
            subuser_q = Q(created_by=user) | Q(campaign__created_by=user)
            if assigned_st_list:
                store_q = Q()
                for st in assigned_st_list:
                    store_q |= Q(summary__icontains=st)
                    store_q |= Q(applied_position__icontains=st)
                    store_q |= Q(call_type__icontains=st)
                subuser_q |= store_q
            qs = qs.filter(subuser_q)

    # STRICT SINGLE-DASHBOARD ISOLATION:
    # Always lock queries strictly to the active dashboard agent!
    target_agent = current_agent_slug or agent_name
    if target_agent and str(target_agent).strip().lower() not in ["none", "null", "all", ""]:
        clean_ag = str(target_agent).strip()
        qs = qs.filter(
            Q(sarvam_agent__slug__iexact=clean_ag) |
            Q(sarvam_agent__name__iexact=clean_ag)
        )
    elif user and not getattr(user, 'is_superuser', False):
        from conversations.views import _get_user_allowed_sarvam_agents
        is_su, allowed_agents = _get_user_allowed_sarvam_agents(user)
        if allowed_agents.exists():
            qs = qs.filter(sarvam_agent=allowed_agents.first())

    # Timeframe filter (created_at is the exact moment call was triggered)
    start_dt, end_dt, label = parse_timeframe(timeframe)
    if start_dt and end_dt:
        qs = qs.filter(created_at__range=(start_dt, end_dt))
    elif start_dt:
        qs = qs.filter(created_at__gte=start_dt)
    elif end_dt:
        qs = qs.filter(created_at__lte=end_dt)

    return qs, label


# =====================================================================
# COPILOT LIVE DATA TOOLS (EXECUTED WHEN AI CALLS THEM)
# =====================================================================

def tool_get_dashboard_summary(user, timeframe="all", current_agent_slug=None, agent_name=None):
    """
    Returns executive metrics summary for the active dashboard: Total calls, Inbound, Outbound,
    Hot/Interested leads, Callbacks, Not interested, Connected calls, and Total Minutes.
    Uses EXACT status classification as sarvam_leads_data (views.py) so numbers match screen cards.
    """
    from conversations.models import SarvamCallRecord, SarvamAgent

    qs, tf_label = get_scoped_records(user, timeframe, current_agent_slug=current_agent_slug, agent_name=agent_name)

    # Status group classification matching views.py lines 3913-3940:
    status_counts = list(qs.values("status").annotate(cnt=Count("id")))
    total_stat_calls = sum(sc["cnt"] for sc in status_counts)

    high_intent_count = 0      # Card 2: Interested / High Intent
    callback_count = 0         # Card 3: Callback / Offers Requested
    not_interested_count = 0   # Card 4: Not Interested (includes dropped, no answer, busy, mismatch)
    completed_neutral_count = 0

    for sc in status_counts:
        st_val = (sc["status"] or "").upper().strip()
        cnt = sc["cnt"]
        if st_val in ["INTERVIEW", "INTERESTED", "HIGH_INTENT", "POSITIVE", "CONFIRMED", "BOOKING_CONFIRMED"]:
            high_intent_count += cnt
        elif st_val in ["CALLBACK", "FOLLOW_UP", "WHATSAPP"]:
            callback_count += cnt
        elif st_val in ["NOT_INTERESTED", "DECLINED", "REJECTED", "NO_ANSWER", "MISSED", "BUSY", "FAILED", "CANCELLED", "TIMEOUT", "UNREACHABLE", "MISMATCH", "ROLE_MISMATCH"]:
            not_interested_count += cnt
        else:
            completed_neutral_count += cnt

    # Inbound vs Outbound breakdown
    inbound_calls = qs.filter(call_type__icontains="Inbound").count()
    outbound_calls = total_stat_calls - inbound_calls

    # Answered / Connected calls (duration > 5s)
    connected_calls = qs.filter(duration_seconds__gt=5).count()

    # Agent minutes from SarvamAgent model (matches dashboard sidebar exactly)
    target_slug = current_agent_slug or agent_name
    ag_obj = None
    if target_slug:
        ag_obj = SarvamAgent.objects.filter(Q(slug__iexact=target_slug) | Q(name__iexact=target_slug)).first()
    elif user and not getattr(user, 'is_superuser', False):
        from conversations.views import _get_user_allowed_sarvam_agents
        _, allowed_agents = _get_user_allowed_sarvam_agents(user)
        ag_obj = allowed_agents.first()

    allocated_minutes = ag_obj.allocated_minutes if ag_obj else 5000.0
    used_minutes = ag_obj.total_used_minutes if ag_obj else round((qs.aggregate(total=Sum('billed_seconds'))['total'] or 0) / 60.0, 1)
    
    # If sub-user, report their personal used minutes instead of whole-agent minutes
    user_prof = getattr(user, 'profile', None)
    user_p = getattr(user_prof, 'custom_permissions', {}) if user_prof else {}
    is_subuser = bool(
        user and getattr(user, 'is_authenticated', False) and
        not getattr(user, 'is_superuser', False) and
        user_prof and user_prof.created_by and
        not user_p.get("is_admin") and
        not user_p.get("can_manage_team")
    )
    if is_subuser:
        used_minutes = round((qs.aggregate(total=Sum('billed_seconds'))['total'] or 0) / 60.0, 1)

    remaining_minutes = ag_obj.remaining_minutes if ag_obj else max(0.0, allocated_minutes - used_minutes)

    # Conversion rate matching UI formula
    conversion_rate = round((high_intent_count / total_stat_calls * 100), 1) if total_stat_calls > 0 else 0.0

    # Scheduled calendar appointments / callbacks
    callbacks_base = qs.filter(callback_datetime__isnull=False)
    pending_appointments_count = callbacks_base.filter(is_callback_completed=False).count()
    completed_callbacks_count = callbacks_base.filter(is_callback_completed=True).count()

    # Test drive inquiries during calls
    test_drive_inquiries_count = qs.filter(
        Q(summary__tags__icontains="Test Drive Request") |
        Q(summary__tags__icontains="Appointment Confirmed")
    ).count()

    # Most recent call on this dashboard
    most_recent = qs.order_by("-created_at").first()
    recent_date_str = timezone.localtime(most_recent.created_at).strftime("%d %B %Y") if most_recent else None
    recent_phone = most_recent.phone_number if most_recent else None

    # If no call in this timeframe, find overall most recent call for this dashboard
    if not most_recent:
        dashboard_all_qs, _ = get_scoped_records(user, "all", current_agent_slug=current_agent_slug, agent_name=agent_name)
        overall_recent = dashboard_all_qs.order_by("-created_at").first()
        if overall_recent:
            recent_date_str = timezone.localtime(overall_recent.created_at).strftime("%d %B %Y")
            recent_phone = overall_recent.phone_number

    active_name = (ag_obj.name if ag_obj else None) or agent_name or current_agent_slug or "This Voice Dashboard"

    result = {
        "timeframe": tf_label,
        "dashboard_agent": active_name,
        "dashboard_card_1_total_inquiries": total_stat_calls,
        "dashboard_card_2_interested_high_intent": high_intent_count,
        "dashboard_card_3_callback_requested": callback_count,
        "dashboard_card_4_not_interested": not_interested_count,
        "total_calls": total_stat_calls,
        "inbound_calls": inbound_calls,
        "outbound_calls": outbound_calls,
        "connected_calls": connected_calls,
        "conversion_rate_percentage": f"{conversion_rate}%",
        "pending_scheduled_appointments": pending_appointments_count,
        "completed_callbacks": completed_callbacks_count,
        "test_drive_inquiries": test_drive_inquiries_count,
        "allocated_minutes": allocated_minutes,
        "used_minutes": used_minutes,
        "remaining_minutes": remaining_minutes,
        "most_recent_call_date": recent_date_str
    }

    if total_stat_calls == 0:
        result["note"] = f"0 calls were recorded on this dashboard ({active_name}) for {tf_label}. The most recent call recorded on this dashboard was on {recent_date_str or 'N/A'}."

    return result


def tool_get_recent_call_logs(user, timeframe="all", current_agent_slug=None, agent_name=None, limit=10):
    """
    Returns actual individual call log records for the active dashboard:
    Phone number, Inbound vs Outbound, Call Type/Campaign, Date/Time, Duration, Status, and Conversation Summary.
    """
    qs, tf_label = get_scoped_records(user, timeframe, current_agent_slug=current_agent_slug, agent_name=agent_name)
    call_records = qs.order_by("-created_at")[:limit]

    logs = []
    for r in call_records:
        s = r.summary or {}
        direction = "Inbound" if "inbound" in (r.call_type or "").lower() else "Outbound"
        raw_call_time = r.start_time or r.created_at
        call_time = timezone.localtime(raw_call_time) if raw_call_time else None
        
        logs.append({
            "phone": r.phone_number,
            "customer_name": r.candidate_name or "Customer",
            "direction": direction,
            "call_type": r.call_type or ("Inbound Call" if direction == "Inbound" else "Outbound Call"),
            "call_date": call_time.strftime("%d %b %Y, %I:%M %p") if call_time else "Recent",
            "duration_seconds": round(r.duration_seconds, 1),
            "status": r.status or r.pipeline_stage,
            "product_interest": s.get("product_interest") or s.get("car_model") or r.applied_position or "Inquiry",
            "summary": s.get("call_summary") or s.get("summary") or "Call logged."
        })

    active_name = agent_name or current_agent_slug or "This Voice Dashboard"
    return {
        "timeframe": tf_label,
        "dashboard_agent": active_name,
        "count_returned": len(logs),
        "calls": logs
    }


def tool_get_hot_leads_list(user, timeframe="all", current_agent_slug=None, agent_name=None, limit=10):
    """
    Returns list of qualified hot/interested leads for this dashboard matching Card 2 on screen,
    with customer names, phone numbers, vehicle/product requirement, and conversation summaries.
    """
    qs, tf_label = get_scoped_records(user, timeframe, current_agent_slug=current_agent_slug, agent_name=agent_name)
    
    # Exact status filter matching Card 2 on screen
    interested_qs = qs.filter(
        status__in=["INTERVIEW", "INTERESTED", "HIGH_INTENT", "POSITIVE", "CONFIRMED", "BOOKING_CONFIRMED"]
    ).order_by("-created_at")[:limit]

    leads = []
    for r in interested_qs:
        s = r.summary or {}
        call_summary = s.get("call_summary") or s.get("summary") or "Customer showed strong interest."
        req = s.get("car_model") or s.get("product_name") or s.get("loan_type") or r.applied_position or "General Inquiry"
        raw_call_time = r.start_time or r.created_at
        call_time = timezone.localtime(raw_call_time) if raw_call_time else None

        leads.append({
            "name": r.candidate_name or "Customer",
            "phone": r.phone_number,
            "status": "HOT / INTERESTED",
            "requirement_or_product": req,
            "summary": call_summary,
            "agent_name": r.sarvam_agent.name if r.sarvam_agent else "Naavya Agent",
            "call_date": call_time.strftime("%d %b %Y, %I:%M %p") if call_time else "Recent"
        })

    active_name = agent_name or current_agent_slug or "This Voice Dashboard"
    return {
        "timeframe": tf_label,
        "dashboard_agent": active_name,
        "count_returned": len(leads),
        "leads": leads
    }


def tool_get_appointments_list(user, timeframe="all", current_agent_slug=None, agent_name=None, limit=10):
    """
    Fetches leads who booked an appointment, scheduled a test drive, or have an active callback/appointment slot.
    Clearly differentiates between pending scheduled appointments and call-time test drive inquiries.
    """
    qs, tf_label = get_scoped_records(user, timeframe, current_agent_slug=current_agent_slug, agent_name=agent_name)

    # 1. Real active/pending scheduled calendar appointments (NOT already completed or dropped)
    pending_qs = qs.filter(
        callback_datetime__isnull=False,
        is_callback_completed=False
    ).exclude(
        status__in=["NOT_INTERESTED", "DECLINED", "REJECTED", "NO_ANSWER", "MISSED", "BUSY", "FAILED"]
    ).order_by("callback_datetime")[:limit]

    # 2. Customers who specifically requested a test drive or appointment during the call
    inquiries_qs = qs.filter(
        Q(summary__tags__icontains="Appointment Confirmed") |
        Q(summary__tags__icontains="Test Drive Request")
    ).exclude(id__in=pending_qs.values_list('id', flat=True)).order_by("-created_at")[:limit]

    pending_list = []
    for r in pending_qs:
        s = r.summary or {}
        raw_call_time = r.start_time or r.created_at
        call_time = timezone.localtime(raw_call_time) if raw_call_time else None
        slot_str = timezone.localtime(r.callback_datetime).strftime("%d %b %Y, %I:%M %p")
        summary_text = s.get("call_summary") or s.get("summary") or r.callback_notes or "Customer requested appointment."

        pending_list.append({
            "name": r.candidate_name or "Customer",
            "phone": r.phone_number,
            "type": "Confirmed Calendar Appointment / Callback",
            "scheduled_calendar_slot": slot_str,
            "call_date_ist": call_time.strftime("%d %b %Y, %I:%M %p") if call_time else "Recent",
            "notes": summary_text,
            "pipeline_stage": r.pipeline_stage or "NEW"
        })

    inquiries_list = []
    for r in inquiries_qs:
        s = r.summary or {}
        raw_call_time = r.start_time or r.created_at
        call_time = timezone.localtime(raw_call_time) if raw_call_time else None
        summary_text = s.get("call_summary") or s.get("summary") or "Customer requested test drive/visit during call."

        inquiries_list.append({
            "name": r.candidate_name or "Customer",
            "phone": r.phone_number,
            "type": "Test Drive / Visit Inquiry (Pending calendar slot booking)",
            "call_date_ist": call_time.strftime("%d %b %Y, %I:%M %p") if call_time else "Recent",
            "notes": summary_text,
            "pipeline_stage": r.pipeline_stage or "NEW"
        })

    agent_display = agent_name or current_agent_slug or "This Voice Agent"

    return {
        "timeframe": tf_label,
        "dashboard_agent": agent_display,
        "pending_scheduled_appointments_count": len(pending_list),
        "pending_scheduled_appointments": pending_list,
        "test_drive_inquiries_count": len(inquiries_list),
        "test_drive_inquiries": inquiries_list,
        "note": (
            "If pending_scheduled_appointments is empty, there are currently 0 pending scheduled calendar slots on this dashboard. "
            "Test drive inquiries represent customers who expressed interest during their calls and requested a test drive, but do not yet have a calendar slot locked in."
        )
    }


def tool_search_leads_by_topic(user, keyword, current_agent_slug=None, agent_name=None, limit=10):
    """
    Searches call transcripts and summaries on this dashboard for specific products, models,
    objections, discounts, or user queries.
    """
    if not keyword or not str(keyword).strip():
        return {"error": "Please provide a search keyword."}

    kw = str(keyword).strip()
    qs, tf_label = get_scoped_records(user, "all", current_agent_slug=current_agent_slug, agent_name=agent_name)

    matched_qs = qs.filter(
        Q(summary__icontains=kw) |
        Q(transcript__icontains=kw) |
        Q(candidate_name__icontains=kw) |
        Q(applied_position__icontains=kw)
    ).order_by("-created_at")[:limit]

    matches = []
    for r in matched_qs:
        s = r.summary or {}
        raw_call_time = r.start_time or r.created_at
        call_time = timezone.localtime(raw_call_time) if raw_call_time else None
        matches.append({
            "name": r.candidate_name or "Customer",
            "phone": r.phone_number,
            "status": r.status or r.pipeline_stage,
            "agent": r.sarvam_agent.name if r.sarvam_agent else "Naavya Voice Bot",
            "snippet": s.get("call_summary") or (r.transcript[:200] + "..." if r.transcript else "No transcript"),
            "date": call_time.strftime("%d %b %Y") if call_time else "Recent"
        })

    return {
        "keyword": kw,
        "count_found": len(matches),
        "results": matches
    }


def tool_get_agent_performance(user, timeframe="all", current_agent_slug=None):
    """
    Returns breakdown of total calls, interested leads, and minutes strictly for the active Naavya Voice Agent on this dashboard.
    """
    from conversations.models import SarvamAgent
    qs, tf_label = get_scoped_records(user, timeframe, current_agent_slug=current_agent_slug)

    agent_obj = None
    if current_agent_slug:
        agent_obj = SarvamAgent.objects.filter(Q(slug__iexact=current_agent_slug) | Q(name__iexact=current_agent_slug)).first()

    status_counts = list(qs.values("status").annotate(cnt=Count("id")))
    total_calls = sum(sc["cnt"] for sc in status_counts)
    high_intent = sum(sc["cnt"] for sc in status_counts if (sc["status"] or "").upper().strip() in ["INTERVIEW", "INTERESTED", "HIGH_INTENT", "POSITIVE", "CONFIRMED", "BOOKING_CONFIRMED"])

    allocated = agent_obj.allocated_minutes if agent_obj else 5000.0
    used_minutes = agent_obj.total_used_minutes if agent_obj else round((qs.aggregate(total=Sum('billed_seconds'))['total'] or 0) / 60.0, 1)
    remaining_minutes = agent_obj.remaining_minutes if agent_obj else max(0.0, allocated - used_minutes)

    conv_rate = round((high_intent / total_calls * 100), 1) if total_calls > 0 else 0.0
    agent_display = f"{agent_obj.name} (Naavya Agent)" if agent_obj else "This Voice Agent"

    return {
        "timeframe": tf_label,
        "active_dashboard_agent": agent_display,
        "total_calls": total_calls,
        "interested_leads": high_intent,
        "conversion_rate": f"{conv_rate}%",
        "allocated_minutes": allocated,
        "minutes_used": used_minutes,
        "remaining_minutes": remaining_minutes,
        "note": f"Performance analytics are strictly isolated to this dashboard ({agent_display}) only."
    }


# =====================================================================
# OPENAI TOOLS DEFINITIONS (FOR FUNCTION CALLING)
# =====================================================================

COPILOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_summary",
            "description": "Get high-level metrics strictly for the current dashboard voice agent: total calls, inbound vs outbound split, hot/interested leads, callbacks, not interested, and minutes used for an exact day, date, month, or timeframe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "description": "Natural date, day, month, or timeframe string (e.g. '17 October 2026', 'yesterday', 'today', 'september 2026', 'this week', 'all')."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_call_logs",
            "description": "Fetch detailed individual call logs strictly for the current dashboard voice agent: customer phone numbers, inbound vs outbound direction, campaign/call type, exact time, duration, and summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "description": "Date or timeframe filter (e.g. '17 October 2026', 'today', 'yesterday', 'all')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of call logs to return (default 5, max 20)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hot_leads_list",
            "description": "Fetch qualified hot/interested leads strictly for the current dashboard voice agent matching Card 2 on screen, with customer names, phone numbers, topics/products, and conversation summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe to filter leads (e.g. 'all', 'today', 'yesterday', 'september 2026')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of leads to return (default 10)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_appointments_list",
            "description": "Fetch leads who booked an appointment, test drive, clinic visit, or store meeting strictly on this dashboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe filter. Defaults to 'all'."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of bookings to return (default 10)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_leads_by_topic",
            "description": "Search call transcripts and summaries strictly on this dashboard for customer objections, product queries, discounts, models, or topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword or phrase (e.g., 'price', 'discount', 'test drive', 'emi', 'loan')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 10)."
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_agent_performance",
            "description": "Get performance metrics, call volume, conversion rate, and minutes used strictly for the active voice agent on this dashboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "description": "Time window (e.g., 'all', 'this_month', 'today'). Defaults to 'all'."
                    }
                }
            }
        }
    }
]


# =====================================================================
# MAIN CHAT ORCHESTRATOR
# =====================================================================

def build_system_prompt(current_agent_slug=None, current_agent_name=None, user=None, screen_stats=None):
    now = timezone.localtime(timezone.now())
    date_str = now.strftime("%A, %d %B %Y")
    
    active_agent = current_agent_name or current_agent_slug or "This Voice Agent"

    # Identify user context (Main Owner vs Sub-User)
    user_context_str = ""
    is_subuser = False
    if user and getattr(user, 'is_authenticated', False):
        user_prof = getattr(user, 'profile', None)
        user_p = getattr(user_prof, 'custom_permissions', {}) if user_prof else {}
        is_subuser = bool(
            not getattr(user, 'is_superuser', False) and
            user_prof and user_prof.created_by and
            not user_p.get("is_admin") and
            not user_p.get("can_manage_team")
        )
        if is_subuser:
            main_owner = user_prof.created_by.username
            user_context_str = (
                f"\n- Active User: **{user.username}** (Sub-User / Team Member with Personal Restricted Activity View).\n"
                f"- Main Account Owner: **{main_owner}**.\n"
                f"- STRICT MULTI-TENANT SUB-USER SCOPING RULE (ABSOLUTE):\n"
                f"  This user ({user.username}) is a sub-user who only has access to their OWN personal activity and leads.\n"
                f"  They CANNOT and MUST NOT see, summarize, or query data from the main owner ({main_owner}) or other team members.\n"
                f"  ALL answers, metrics, summaries, hot leads, and appointment details MUST be strictly limited to {user.username}'s personal records only.\n"
                f"  Never reveal or refer to whole-agent data, platform totals, or other team members' calls."
            )
        else:
            user_context_str = (
                f"\n- Active User: **{user.username}** (Main Account Owner / Team Manager).\n"
                f"- Access Tier: **Full Team Dashboard Access** (can see all activity across all users and sub-users on this voice agent)."
            )

    screen_stats_str = ""
    if screen_stats and isinstance(screen_stats, dict):
        total_val = screen_stats.get('total')
        high_intent_val = screen_stats.get('high_intent')
        callback_val = screen_stats.get('callback')
        not_int_val = screen_stats.get('not_interested')
        sel_date_val = screen_stats.get('selected_date') or 'All Time (No date filter)'
        screen_stats_str = f"""
### CURRENT ON-SCREEN DASHBOARD METRICS (CURRENTLY VISIBLE TO USER):
- Total Inquiries (Card 1): **{total_val}**
- Interested / High Intent (Card 2): **{high_intent_val}**
- Callback / Offers Requested (Card 3): **{callback_val}**
- Not Interested (Card 4): **{not_int_val}**
- Active On-Screen Date Filter: **{sel_date_val}**
- Voice Agent Dashboard: **{active_agent}**

CRITICAL CONSISTENCY DIRECTIVE:
The user is looking directly at these exact 4 stat cards on their screen right now.
Your answers regarding summary stats or lead counts must BE 100% FAITHFUL TO AND CONSISTENT WITH these cards.
"""

    return f"""You are the **Naavya AI Dashboard Intelligence Copilot** for the VoiceBot SaaS platform.
Current System Date: **{date_str}**.

You are embedded exclusively on the Voice Dashboard for: **{active_agent}** (slug: `{current_agent_slug or ''}`).{user_context_str}
{screen_stats_str}
### STRICT BOUNDARY RULES (MANDATORY & ABSOLUTE):
1. **STRICT SINGLE-DASHBOARD ISOLATION**:
   - You ONLY represent and answer for the active dashboard: **{active_agent}**.
   - You do NOT have access to, and must NEVER share, compare, mention, or list data, calls, metrics, or leads from any other voice agents or other dashboards.
   - For Sub-users: Always scope answers strictly to this particular dashboard (**{active_agent}**) owned by their main account owner. Do not provide whole-system or platform-wide metrics.
   - If the user asks to "compare performance across all voice agents", asks about other agents, or asks about other dashboards:
     Politely refuse cross-agent comparison: State clearly that this AI Copilot is strictly isolated to the **{active_agent}** dashboard only and cannot access or compare other voice agents or dashboards.
     Then, display the performance stats exclusively for **{active_agent}** (calls, interested leads, conversion rate, minutes).
     NEVER mention, list, or compare names or stats of other voice agents or client dashboards.
2. **CRITICAL BRANDING RULE**:
   - Under NO circumstances should you EVER use or output the word 'Sarvam' or 'Sarvam Agent'.
   - ALWAYS refer to the voice agent as **Naavya AI Agent** or **Naavya Agent** (e.g. '{active_agent} Naavya Agent', 'Naavya Voice Assistant').
3. **Never guess, invent, or hallucinate numbers**:
   - Always call `get_dashboard_summary`, `get_recent_call_logs`, `get_hot_leads_list`, `get_agent_performance`, or `get_appointments_list` to get exact database records for **{active_agent}**.
   - If the database returns 0 calls, honestly state that **0 calls** were triggered on that date.
4. **Dashboard Card Metrics Alignment**:
   - Total Inquiries = Card 1 (`dashboard_card_1_total_inquiries`)
   - Interested / High Intent = Card 2 (`dashboard_card_2_interested_high_intent`)
   - Callback Requested = Card 3 (`dashboard_card_3_callback_requested`)
   - Not Interested / Dropped = Card 4 (`dashboard_card_4_not_interested`)
   - Minutes Used = `used_minutes` (from the dashboard sidebar)
   Always report these exact figures so your answer matches what the user sees on their dashboard screen!
5. **Format & Tone**:
   - Bold key numbers (**59 Calls**, **2 Hot Leads**, **2 Callbacks**, **53 Not Interested**, **3.4% Conversion**).
   - Use clean bullet points with icons: 📞 Calls, 🔥 Hot leads, 📅 Appointments, 🎙️ Naavya Agent, 💡 Tips.
   - Helpful, executive, factual, and direct.
6. **Appointments & Test Drives Accuracy**:
   - Differentiate clearly between **Confirmed Appointments / Follow-ups** (leads with a fixed calendar slot in `scheduled_calendar_slot`) and **Test Drive / Visit Inquiries** (customers who expressed interest during their call, but have no fixed calendar slot booked yet).
   - NEVER present the call trigger timestamp (e.g. '05:50 AM' or '11:20 AM') as an appointment date or scheduled slot! The call date was only when the phone call took place.
   - If there are 0 pending scheduled calendar slots, state honestly: 'There are currently 0 pending scheduled calendar appointments on this dashboard.'
   - Then list any customers who requested a test drive during their calls as 'Test Drive Inquiries (Pending calendar slot booking)'.
"""


def process_copilot_query(user_query, user=None, history=None, current_agent_slug=None, current_agent_name=None, screen_stats=None):
    """
    Processes a natural language question from the user using Azure OpenAI
    with automatic tool execution loop.
    """
    client = get_azure_client()
    system_content = build_system_prompt(
        current_agent_slug=current_agent_slug,
        current_agent_name=current_agent_name,
        user=user,
        screen_stats=screen_stats
    )
    messages = [{"role": "system", "content": system_content}]

    # Append recent conversation history (up to last 6 messages)
    if history and isinstance(history, list):
        for h in history[-6:]:
            role = h.get("role")
            content = h.get("content")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": str(content)})

    # Append current user question
    messages.append({"role": "user", "content": user_query})

    tools_used = []

    try:
        # Step 1: Initial call to Azure OpenAI with tools
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            tools=COPILOT_TOOLS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=650
        )

        msg = response.choices[0].message

        # Step 2: Handle Tool Calls
        if msg.tool_calls:
            messages.append(msg)

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = {}
                try:
                    fn_args = json.loads(tc.function.arguments)
                except Exception:
                    pass

                tools_used.append({"tool": fn_name, "args": fn_args})

                # Execute matching tool (strictly locked to current_agent_slug)
                tool_output = None
                if fn_name == "get_dashboard_summary":
                    tool_output = tool_get_dashboard_summary(
                        user=user,
                        timeframe=fn_args.get("timeframe", "all"),
                        current_agent_slug=current_agent_slug,
                        agent_name=current_agent_name
                    )
                elif fn_name == "get_recent_call_logs":
                    tool_output = tool_get_recent_call_logs(
                        user=user,
                        timeframe=fn_args.get("timeframe", "all"),
                        current_agent_slug=current_agent_slug,
                        agent_name=current_agent_name,
                        limit=fn_args.get("limit", 5)
                    )
                elif fn_name == "get_hot_leads_list":
                    tool_output = tool_get_hot_leads_list(
                        user=user,
                        timeframe=fn_args.get("timeframe", "all"),
                        current_agent_slug=current_agent_slug,
                        agent_name=current_agent_name,
                        limit=fn_args.get("limit", 10)
                    )
                elif fn_name == "get_appointments_list":
                    tool_output = tool_get_appointments_list(
                        user=user,
                        timeframe=fn_args.get("timeframe", "all"),
                        current_agent_slug=current_agent_slug,
                        agent_name=current_agent_name,
                        limit=fn_args.get("limit", 10)
                    )
                elif fn_name == "search_leads_by_topic":
                    tool_output = tool_search_leads_by_topic(
                        user=user,
                        keyword=fn_args.get("keyword", ""),
                        current_agent_slug=current_agent_slug,
                        agent_name=current_agent_name,
                        limit=fn_args.get("limit", 10)
                    )
                elif fn_name == "get_agent_performance":
                    tool_output = tool_get_agent_performance(
                        user=user,
                        timeframe=fn_args.get("timeframe", "all"),
                        current_agent_slug=current_agent_slug
                    )
                else:
                    tool_output = {"error": f"Unknown tool: {fn_name}"}

                # Feed tool result back to model
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_output)
                })

            # Step 3: Get final response from Azure OpenAI
            second_response = client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                temperature=0.1,
                max_tokens=800
            )
            final_reply = second_response.choices[0].message.content
            return {
                "reply": final_reply,
                "tools_used": tools_used
            }

        else:
            return {
                "reply": msg.content,
                "tools_used": []
            }

    except Exception as e:
        logger.error(f"❌ [AI COPILOT ERROR]: {e}", exc_info=True)
        return {
            "reply": f"I encountered an error querying your dashboard data: {str(e)}. Please try asking again in a moment.",
            "tools_used": []
        }

