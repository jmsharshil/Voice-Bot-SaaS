import logging
from conversations.models import KylasCityAgentMapping, KylasWebhookConfig, SarvamAgent

logger = logging.getLogger(__name__)


def extract_target_center(raw_data):
    """
    Extracts the targeted campaign center/city from the Kylas lead payload.

    Priority Order:
    1. entity.campaign.value (PRIMARY: e.g. "Rajkot", "Ahmedabad", "Surat" in Facebook Leads)
    2. entity.utmCampaign or entity.utmSource (e.g. "iiiEM Rajkot")
    3. entity.city (Fallback ONLY if no campaign value is present)
    4. customFieldValues
    """
    entity = (
        raw_data.get("entity")
        if isinstance(raw_data.get("entity"), dict)
        else raw_data
    )
    if not isinstance(entity, dict):
        entity = raw_data

    # 1. Primary: campaign.value
    camp = entity.get("campaign")
    if isinstance(camp, dict) and camp.get("value"):
        val = str(camp["value"]).strip()
        if val:
            return val, "campaign.value"
    elif isinstance(camp, str) and camp.strip():
        return camp.strip(), "campaign"

    # 2. Secondary: UTM parameters (if campaign is missing or empty)
    for utm_key in ["utmCampaign", "utmSource", "utmMedium"]:
        val = str(entity.get(utm_key) or "").strip()
        if val:
            return val, utm_key

    # 3. Tertiary: direct entity.city (ONLY when campaign.value is not present)
    direct_city = str(
        entity.get("city") or raw_data.get("city") or ""
    ).strip()
    if direct_city:
        return direct_city, "entity.city"

    # 4. Custom fields
    custom_fields = entity.get("customFieldValues") or {}
    if isinstance(custom_fields, dict):
        for k, v in custom_fields.items():
            if isinstance(v, dict) and v.get("value"):
                c_val = str(v["value"]).strip()
                if c_val:
                    return c_val, f"customField.{k}"
            elif isinstance(v, str) and v.strip():
                return v.strip(), f"customField.{k}"

    return "Unknown", "none"


def resolve_agent_by_city(raw_data, fallback_agent=None):
    """
    City-to-Agent Router & Calling Whitelist Controller for Kylas CRM Webhook.

    Determines the target voice agent strictly based on the lead's Campaign Center
    (e.g. entity.campaign.value).

    Returns:
        (should_call: bool, target_agent: SarvamAgent | None, detected_city: str, reason: str)
    """
    config = KylasWebhookConfig.get_config()

    # 1. Master toggle check
    if not config.is_enabled:
        return (
            False,
            None,
            "Unknown",
            "Kylas outbound calling is paused in Django Admin (Master Switch OFF)",
        )

    # 2. Extract the decisive campaign center
    target_center, source_field = extract_target_center(raw_data)
    target_clean = target_center.strip().lower()

    # 3. Search active mappings in database for this specific center
    active_mappings = list(
        KylasCityAgentMapping.objects.filter(is_active=True)
        .select_related("sarvam_agent")
        .filter(sarvam_agent__is_active=True)
    )

    matched_mapping = None
    if target_clean and target_clean != "unknown":
        for mapping in active_mappings:
            city_tokens = [
                c.strip().lower()
                for c in mapping.city_name.replace("/", ",").split(",")
                if c.strip()
            ]
            for token in city_tokens:
                # Match: e.g. token 'rajkot' in 'rajkot' or 'iiiem rajkot'
                if token == target_clean or token in target_clean or target_clean in token:
                    matched_mapping = mapping
                    break
            if matched_mapping:
                break

    # If matched with an active city mapping
    if matched_mapping:
        logger.info(
            f"🎯 [KYLAS CITY ROUTER]: Matched city '{matched_mapping.city_name}' "
            f"from {source_field}='{target_center}' -> Routing to Agent '{matched_mapping.sarvam_agent.name}' (ID {matched_mapping.sarvam_agent.id})"
        )
        return (
            True,
            matched_mapping.sarvam_agent,
            matched_mapping.city_name,
            f"Matched active city mapping: '{matched_mapping.city_name}' (from {source_field})",
        )

    # If no active mapping matched the target campaign center:
    if config.calling_mode == "MAPPED_ONLY":
        reason = f"Campaign Center '{target_center}' (from {source_field}) is not in active calling list (Strict Mapped-Only Mode)"
        logger.info(f"⏭️ [KYLAS CITY ROUTER]: Calling SKIPPED. {reason}")
        return (False, None, target_center, reason)

    # ALL_CITIES mode: Fallback to configured default agent or fallback_agent
    default_agent = (
        config.default_fallback_agent
        or fallback_agent
        or SarvamAgent.objects.filter(is_active=True).first()
    )
    logger.info(
        f"ℹ️ [KYLAS CITY ROUTER]: Campaign Center '{target_center}' has no specific mapping. "
        f"Calling via fallback Agent '{default_agent.name if default_agent else 'None'}' (All Cities Mode)"
    )
    return (
        True,
        default_agent,
        target_center,
        f"Allowed via All Cities fallback (Center: {target_center})",
    )
