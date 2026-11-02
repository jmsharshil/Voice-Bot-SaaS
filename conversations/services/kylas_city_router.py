import logging
from conversations.models import KylasCityAgentMapping, SarvamAgent

logger = logging.getLogger(__name__)

def resolve_agent_by_city(raw_data, fallback_agent=None):
    """
    Standalone City-to-Agent Resolver for Kylas CRM Webhook.
    
    Checks (in priority order):
    1. entity.campaign.value (e.g. 'Rajkot', 'Vadodara', 'Ahmedabad', 'Delhi', 'Kolkata')
    2. entity.utmCampaign / utmSource
    3. entity.city
    4. customFieldValues (any city/center custom fields)
    5. fallback_agent (or first active SarvamAgent)
    
    Returns: (matched_agent, detected_city_name)
    """
    entity = raw_data.get("entity") if isinstance(raw_data.get("entity"), dict) else raw_data
    if not isinstance(entity, dict):
        entity = raw_data

    candidate_cities = []

    # 1. Campaign value (highest accuracy in Kylas lead payloads)
    camp = entity.get("campaign")
    if isinstance(camp, dict) and camp.get("value"):
        candidate_cities.append(str(camp["value"]).strip())
    elif isinstance(camp, str) and camp.strip():
        candidate_cities.append(camp.strip())

    # 2. UTM campaign / UTM Source keywords
    for utm_key in ["utmCampaign", "utmSource", "utmMedium"]:
        val = str(entity.get(utm_key) or "").strip()
        if val:
            candidate_cities.append(val)

    # 3. Direct city field
    direct_city = str(entity.get("city") or raw_data.get("city") or "").strip()
    if direct_city:
        candidate_cities.append(direct_city)

    # 4. Custom field values
    custom_fields = entity.get("customFieldValues") or {}
    if isinstance(custom_fields, dict):
        for k, v in custom_fields.items():
            if isinstance(v, dict) and v.get("value"):
                candidate_cities.append(str(v["value"]).strip())
            elif isinstance(v, str) and v.strip():
                candidate_cities.append(v.strip())

    # Search active mappings in database
    active_mappings = list(
        KylasCityAgentMapping.objects.filter(is_active=True)
        .select_related("sarvam_agent")
        .filter(sarvam_agent__is_active=True)
    )

    for cand in candidate_cities:
        cand_clean = cand.strip().lower()
        if not cand_clean:
            continue

        # Exact match or substring match
        for mapping in active_mappings:
            target_city = mapping.city_name.strip().lower()
            if not target_city:
                continue

            # Match: e.g. 'Rajkot' in 'iiiEM Rajkot 10.9.2026' or exact 'Rajkot' == 'rajkot'
            if target_city == cand_clean or target_city in cand_clean or cand_clean in target_city:
                logger.info(
                    f"🎯 [KYLAS CITY ROUTER]: Successfully matched city '{mapping.city_name}' "
                    f"from payload value '{cand}' -> Routing to Agent '{mapping.sarvam_agent.name}' (ID {mapping.sarvam_agent.id})"
                )
                return mapping.sarvam_agent, mapping.city_name

    # If no mapping matched, fallback safely
    default_agent = fallback_agent or SarvamAgent.objects.filter(is_active=True).first()
    matched_city_label = candidate_cities[0] if candidate_cities else "Unknown"
    logger.info(
        f"ℹ️ [KYLAS CITY ROUTER]: No specific city mapping found for candidates {candidate_cities}. "
        f"Using fallback Agent '{default_agent.name if default_agent else 'None'}'"
    )
    return default_agent, matched_city_label

