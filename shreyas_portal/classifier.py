import re
import logging
from django.db.models import Q
from .models import ShreyasDepartment, ShreyasCallLead

logger = logging.getLogger(__name__)


def format_transcript_to_str(val) -> str:
    """
    Safely converts any transcript format (list of turns, dict, JSON string, or raw string)
    into a formatted human-readable conversation string.
    """
    import json
    import ast
    if isinstance(val, str):
        val_str = val.strip()
        if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith("{") and val_str.endswith("}")):
            try:
                val = json.loads(val_str)
            except Exception:
                try:
                    val = ast.literal_eval(val_str)
                except Exception:
                    pass

    if isinstance(val, list):
        turns = []
        for item in val:
            if isinstance(item, dict):
                r = str(item.get("role", "Speaker")).strip().capitalize()
                en = str(item.get("en_text") or item.get("text") or item.get("content") or "").strip()
                indic = str(item.get("indic_text") or "").strip()
                text = f"{en} ({indic})" if en and indic and en != indic else (en or indic)
                if text:
                    turns.append(f"{r}: {text}")
            elif isinstance(item, str) and item.strip():
                turns.append(item.strip())
        return "\n\n".join(turns)
    elif isinstance(val, dict):
        return str(val.get("transcript") or val.get("text") or val)
    return str(val or "").strip()


def format_summary_to_str(val) -> str:
    """
    Safely extracts summary text whether provided as a dict, JSON, or string.
    """
    if isinstance(val, dict):
        return str(
            val.get("call_summary")
            or val.get("summary")
            or val.get("description")
            or " ".join([str(v) for v in val.values() if isinstance(v, str)])
            or ""
        ).strip()
    return str(val or "").strip()


def classify_caller_interest(transcript_text: str = "", summary_text: str = "", explicit_interest: str = "") -> tuple:
    """
    Analyzes caller transcript & call summary against all active Shreyas Departments.
    Prioritizes:
    1. Explicit interest returned by Sarvam AI (e.g. interest_field = "museum", "education")
    2. Words spoken by USER (gives 10x higher weight than agent greeting)
    3. Summary text
    Returns: (matched_department, matched_keywords_str, detected_intent_description)
    """
    transcript_text = format_transcript_to_str(transcript_text)
    summary_text = format_summary_to_str(summary_text)
    departments = ShreyasDepartment.objects.filter(is_active=True).order_by("order", "id")
    if not departments.exists():
        return None, "", "No active departments configured"

    # 1. Direct match with Sarvam explicit interest_field
    if explicit_interest and str(explicit_interest).strip():
        exp_clean = str(explicit_interest).strip().lower()
        for dept in departments:
            if exp_clean in dept.slug.lower() or exp_clean in dept.name.lower() or dept.slug.lower() in exp_clean or dept.name.lower() in exp_clean:
                return dept, explicit_interest, f"Inquiry about {dept.name} (Direct Interest: {explicit_interest})"
            if exp_clean in dept.get_keywords_list():
                return dept, explicit_interest, f"Inquiry about {dept.name} (Matched: {explicit_interest})"

    # 2. Extract user utterances vs agent utterances from transcript
    user_utterances = []
    agent_utterances = []
    lines = (transcript_text or "").split("\n")
    current_role = "user"
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        line_lower = line_clean.lower()
        if line_lower.startswith("user:") or line_lower.startswith("caller:"):
            current_role = "user"
            user_utterances.append(line_clean)
        elif line_lower.startswith("agent:") or line_lower.startswith("bot:"):
            current_role = "agent"
            agent_utterances.append(line_clean)
        else:
            if current_role == "user":
                user_utterances.append(line_clean)
            else:
                agent_utterances.append(line_clean)

    user_text = " ".join(user_utterances).lower()
    summary_lower = (summary_text or "").lower()

    best_dept = None
    best_score = 0
    best_matched_words = []

    for dept in departments:
        keywords = dept.get_keywords_list()
        dept_score = 0
        matched_in_dept = []
        dept_name_lower = dept.name.lower()

        # Check in user's spoken words
        if dept_name_lower in user_text:
            dept_score += 25
            matched_in_dept.append(dept.name)
        elif dept_name_lower in summary_lower:
            dept_score += 15
            matched_in_dept.append(dept.name)

        for kw in keywords:
            if not kw:
                continue
            pattern = r'\b' + re.escape(kw) + r'\b'
            user_matches = len(re.findall(pattern, user_text))
            summary_matches = len(re.findall(pattern, summary_lower))
            agent_matches = len(re.findall(pattern, " ".join(agent_utterances).lower()))

            if user_matches > 0:
                dept_score += (user_matches * 10)
                matched_in_dept.append(kw)
            if summary_matches > 0:
                dept_score += (summary_matches * 8)
                matched_in_dept.append(kw)
            if agent_matches > 0 and user_matches == 0 and summary_matches == 0:
                dept_score += agent_matches
                matched_in_dept.append(kw)

        if dept_score > best_score:
            best_score = dept_score
            best_dept = dept
            best_matched_words = list(set(matched_in_dept))

    if best_dept and best_score > 0:
        matched_str = ", ".join(best_matched_words)
        intent_desc = f"Inquiry about {best_dept.name} (Matched: {matched_str})"
        return best_dept, matched_str, intent_desc

    # Fallback: check if a default/general department exists
    general_dept = departments.filter(slug__in=["general", "inquiries", "other"]).first()
    if general_dept:
        return general_dept, "general", "General Inquiry"

    return None, "", "General / Uncategorized Inquiry"


def detect_lead_sentiment(transcript: str, summary: str, duration_sec: float) -> str:
    """
    Classifies lead sentiment into HOT, WARM, or COLD.
    """
    transcript = format_transcript_to_str(transcript)
    summary = format_summary_to_str(summary)
    text = f"{transcript} {summary}".lower()
    hot_words = ["interested", "admission", "register", "join", "fee details", "trial", "book", "whatsapp", "enroll", "yes please", "sure"]
    cold_words = ["not interested", "wrong number", "don't call", "disconnect", "no thank you", "bye"]

    hot_hits = sum(1 for w in hot_words if w in text)
    cold_hits = sum(1 for w in cold_words if w in text)

    if cold_hits > 0 and hot_hits == 0:
        return "COLD"
    if hot_hits >= 2 or duration_sec >= 45:
        return "HOT"
    if duration_sec >= 15:
        return "WARM"
    return "COLD"


def route_and_save_shreyas_lead(
    phone_number: str,
    caller_name: str = "Caller",
    transcript: str = "",
    summary: str = "",
    audio_url: str = "",
    duration_seconds: float = 0.0,
    status: str = "COMPLETED",
    interaction_id: str = "",
    sarvam_call_record=None,
    call_type: str = "Inbound Call",
    explicit_interest: str = ""
) -> ShreyasCallLead:
    """
    Classifies interest and creates or updates a ShreyasCallLead.
    Guarantees that the lead is linked to the correct department without mismatch.
    """
    transcript = format_transcript_to_str(transcript)
    summary = format_summary_to_str(summary)
    dept, matched_keywords, detected_intent = classify_caller_interest(transcript, summary, explicit_interest)
    sentiment = detect_lead_sentiment(transcript, summary, duration_seconds)

    lead = None
    if sarvam_call_record:
        lead = ShreyasCallLead.objects.filter(sarvam_call_record=sarvam_call_record).first()

    if not lead and interaction_id:
        raw_iid = str(interaction_id).split("/")[-1].strip()
        lead = (
            ShreyasCallLead.objects.filter(interaction_id=interaction_id).first()
            or (ShreyasCallLead.objects.filter(interaction_id__endswith=raw_iid).first() if raw_iid else None)
        )

    clean_phone = str(phone_number or "").strip()
    is_valid_phone = clean_phone and clean_phone.lower() not in ["unknown", "none", "null", ""]

    if not lead and not interaction_id:
        from datetime import timedelta
        from django.utils import timezone
        recent_threshold = timezone.now() - timedelta(minutes=2)
        # Check if an earlier webhook created an "Unknown Caller" or 0s placeholder lead for this caller
        if caller_name and caller_name.lower() not in ["caller", "customer", "valued customer", "unknown", ""]:
            lead = ShreyasCallLead.objects.filter(
                created_at__gte=recent_threshold,
                caller_name__iexact=caller_name.strip(),
                phone_number__in=["Unknown Caller", "unknown", ""],
                duration_seconds=0.0
            ).order_by("-created_at").first()

    if not lead and interaction_id:
        from datetime import timedelta
        from django.utils import timezone
        recent_threshold = timezone.now() - timedelta(minutes=2)
        lead = ShreyasCallLead.objects.filter(
            created_at__gte=recent_threshold,
            phone_number__in=["Unknown Caller", "unknown", ""],
            duration_seconds=0.0,
            interaction_id__startswith="manual_"
        ).order_by("-created_at").first()

    # Guard: Never hijack an existing lead that already belongs to a DIFFERENT completed interaction
    if lead and lead.interaction_id and interaction_id:
        raw_prev = str(lead.interaction_id).split("/")[-1].strip()
        raw_curr = str(interaction_id).split("/")[-1].strip()
        if raw_prev != raw_curr and not lead.interaction_id.startswith("manual_"):
            lead = None

    if not lead:
        lead = ShreyasCallLead.objects.create(
            sarvam_call_record=sarvam_call_record,
            department=dept,
            phone_number=clean_phone if is_valid_phone else "Unknown Caller",
            caller_name=caller_name,
            call_type=call_type,
            duration_seconds=duration_seconds,
            status=status,
            lead_sentiment=sentiment,
            audio_url=audio_url,
            summary=summary,
            transcript=transcript,
            detected_intent=detected_intent,
            matched_keywords=matched_keywords,
            interaction_id=interaction_id or f"manual_{clean_phone}_{sarvam_call_record.id if sarvam_call_record else 'new'}"
        )
    else:
        # Merge / Update with the full CDR
        if is_valid_phone:
            lead.phone_number = clean_phone

        if dept:
            lead.department = dept
            lead.detected_intent = detected_intent
            lead.matched_keywords = matched_keywords

        if caller_name and caller_name.lower() not in ["caller", "customer", "valued customer", "none", "null", ""]:
            lead.caller_name = caller_name
        elif not lead.caller_name or lead.caller_name in ["Caller", "Customer", "Valued Customer"]:
            lead.caller_name = caller_name or "Caller"

        if duration_seconds > 0:
            lead.duration_seconds = duration_seconds
        if status:
            lead.status = status
        if sentiment:
            lead.lead_sentiment = sentiment
        if audio_url:
            lead.audio_url = audio_url
        if summary:
            lead.summary = summary
        if transcript:
            lead.transcript = transcript
        if sarvam_call_record:
            lead.sarvam_call_record = sarvam_call_record
        if interaction_id:
            lead.interaction_id = interaction_id
        lead.save()

    logger.info(f"✅ [SHREYAS LEAD ROUTED]: Phone={phone_number} -> Department='{dept.name if dept else 'Unassigned'}' (Score Keywords: {matched_keywords})")
    return lead
