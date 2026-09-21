import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

_SARVAM_RATE_LIMITED_UNTIL = 0

# Kylas CRM Configuration
KYLAS_API_BASE_URL = os.getenv("KYLAS_API_BASE_URL", "https://api.kylas.io/v1")
KYLAS_API_KEY = os.getenv("KYLAS_API_KEY", "")

# Sarvam AI Agent (Samvaad) Configuration
SARVAM_API_BASE_URL = os.getenv("SARVAM_API_BASE_URL", "https://apps.sarvam.ai")
SARVAM_AGENT_API_KEY = os.getenv("SARVAM_AGENT_API_KEY") or "sk_samvaad_9oozxe0h_jqecMJbqT5yaD6gvE4fLPRlO"
SARVAM_AGENT_ID = os.getenv("SARVAM_AGENT_ID") or "iiiEM---Rec-136dc7be-adb6"
SARVAM_ORG_ID = os.getenv("SARVAM_ORG_ID") or "01a03cbf-1bf4-70f0-995f-854d6d2dd105"
SARVAM_WORKSPACE_ID = os.getenv("SARVAM_WORKSPACE_ID") or "01a03cbf-1bfb-770a-bb91-06baeec9d28e"

# Webhook Domain
MY_PUBLIC_DOMAIN = os.getenv("MY_PUBLIC_DOMAIN", "https://unprecious-waltraud-nasological.ngrok-free.dev")


class KylasService:
    """
    [ON HOLD / DISABLED FOR NOW]
    Service class for interacting with Kylas CRM REST APIs.
    Preserved for future re-activation.
    """

    @staticmethod
    def get_headers():
        return {
            "api-key": KYLAS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @classmethod
    def log_call_activity(cls, lead_id: int, call_data: dict):
        """
        [ON HOLD] Creates a Call Activity in Kylas under the specified Lead ID.
        """
        logger.info(f"ℹ️ [KYLAS INTEGRATION ON HOLD] Skipped logging call activity for Lead #{lead_id}")
        return {"status": "disabled", "message": "Kylas CRM integration is on hold"}

    @classmethod
    def update_lead_status(cls, lead_id: int, stage_id: str = None, custom_fields: dict = None):
        """
        [ON HOLD] Updates lead stage or custom fields in Kylas CRM.
        """
        logger.info(f"ℹ️ [KYLAS INTEGRATION ON HOLD] Skipped updating Lead #{lead_id}")
        return {"status": "disabled", "message": "Kylas CRM integration is on hold"}


SARVAM_CONNECTION_ID = os.getenv("SARVAM_CONNECTION_ID", "b2c7589b-ba-50612cf7-e15f")
SARVAM_AGENT_PHONE_NUMBER = os.getenv("SARVAM_AGENT_PHONE_NUMBER", "+917971414121")


class SarvamAgentService:
    """
    Service class for initiating outbound calls and fetching analytics via Sarvam AI Agent platform.
    All methods accept an optional `sarvam_agent` (SarvamAgent DB model instance).
    When provided, its credentials override the global .env defaults — enabling multi-agent support.
    """

    @classmethod
    def _creds(cls, sarvam_agent=None):
        """Returns (org_id, workspace_id, app_id, api_key, connection_id, agent_phone, domain) for the given agent."""
        if sarvam_agent:
            return (
                sarvam_agent.org_id,
                sarvam_agent.workspace_id,
                sarvam_agent.app_id,
                sarvam_agent.api_key,
                sarvam_agent.connection_id,
                sarvam_agent.agent_phone,
                sarvam_agent.webhook_domain or MY_PUBLIC_DOMAIN,
            )
        return (
            SARVAM_ORG_ID,
            SARVAM_WORKSPACE_ID,
            SARVAM_AGENT_ID,
            SARVAM_AGENT_API_KEY,
            SARVAM_CONNECTION_ID,
            SARVAM_AGENT_PHONE_NUMBER,
            MY_PUBLIC_DOMAIN,
        )

    @classmethod
    def get_agent_headers(cls, api_key=None):
        key = api_key or SARVAM_AGENT_API_KEY
        return {
            "X-API-Key": key,
            "api-subscription-key": key,
            "Content-Type": "application/json"
        }

    @classmethod
    def trigger_outbound_call(cls, phone_number: str, lead_id: int = 0, customer_name: str = "", language: str = "hi-IN", context: dict = None, sarvam_agent=None, extra_variables: dict = None):
        """
        Triggers an outbound voice call from Sarvam AI Agent to the target phone number.
        If `sarvam_agent` (SarvamAgent instance) is provided, its credentials are used;
        otherwise falls back to global .env configuration.
        Accepts optional `extra_variables` (e.g. {"car_model": "Scorpio-N", "city": "Ahmedabad"})
        which are dynamically passed to Sarvam agent prompt variables.
        """
        if sarvam_agent and getattr(sarvam_agent, "is_minutes_exhausted", False):
            logger.warning(f"🛑 [MINUTES EXHAUSTED]: Agent '{sarvam_agent.name}' has 0 remaining call minutes ({sarvam_agent.remaining_minutes}m left). Call blocked.")
            return {
                "status": "error",
                "code": "MINUTES_EXHAUSTED",
                "error": "Call minutes limit reached for this agent. To continue service, please add minutes.",
                "message": "Call minutes limit reached for this agent. To continue service, please add minutes.",
                "remaining_minutes": 0,
            }

        org_id, workspace_id, app_id, api_key, connection_id, agent_phone, domain = cls._creds(sarvam_agent)

        if not api_key:
            logger.warning("⚠️ SARVAM_AGENT_API_KEY is missing. Call trigger logged in simulation mode.")
            print(f"📱 [SIMULATED CALL TRIGGER]: Sarvam AI calling {phone_number} (Lead #{lead_id}) in language {language}")
            return {"status": "simulated", "phone_number": phone_number, "lead_id": lead_id}

        url = f"{SARVAM_API_BASE_URL}/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds"
        
        # Build canonical webhook callback URL without duplicate paths or trailing whitespace
        clean_domain = str(domain or "").strip()
        for suffix in ["/api/webhook/sarvam/cdr/", "/api/webhook/sarvam/cdr", "/api/webhook/sarvam/", "/api/webhook/sarvam", "/"]:
            if clean_domain.endswith(suffix):
                clean_domain = clean_domain[:-len(suffix)]
        clean_domain = clean_domain.strip().rstrip("/")
        if clean_domain and not clean_domain.startswith("http://") and not clean_domain.startswith("https://"):
            clean_domain = f"https://{clean_domain}"
        callback_url = f"{clean_domain}/api/webhook/sarvam/cdr/" if clean_domain else ""

        # Ensure phone number is E.164 formatted (with +91)
        formatted_phone = str(phone_number).strip()
        if not formatted_phone.startswith("+"):
            if len(formatted_phone) == 10:
                formatted_phone = f"+91{formatted_phone}"
            elif not formatted_phone.startswith("+"):
                formatted_phone = f"+{formatted_phone}"

        customer_name = str(customer_name or "").strip()
        if not customer_name or customer_name.lower() in ["nan", "none", "null"]:
            customer_name = "Valued Customer"

        # Base variable standard in Sarvam
        agent_vars = {
            "user_name": customer_name,
        }

        # Inject all dynamic columns from the uploaded spreadsheet
        if extra_variables and isinstance(extra_variables, dict):
            for k, v in extra_variables.items():
                if v is not None and str(v).strip() != "" and str(v).lower() not in ["nan", "none", "null"]:
                    k_str = str(k).strip()
                    v_str = str(v).strip()
                    agent_vars[k_str] = v_str

        # Automotive alias helpers: map car_name, model, or car to car_model automatically
        if "car_name" in agent_vars and "car_model" not in agent_vars:
            agent_vars["car_model"] = agent_vars["car_name"]
        if "model" in agent_vars and "car_model" not in agent_vars:
            agent_vars["car_model"] = agent_vars["model"]
        if "car" in agent_vars and "car_model" not in agent_vars:
            agent_vars["car_model"] = agent_vars["car"]

        payload = {
            "app_config": {
                "app_id": app_id,
                "version_filter": "latest",
                "connection_config": {
                    "connection_id": connection_id,
                    "agent_phone_number": agent_phone
                },
                "agent_variables": agent_vars,
                "webhook_config": {
                    "url": callback_url
                }
            },
            "user_config": {
                "user_phone_number": formatted_phone
            }
        }

        try:
            print(f"📤 [SARVAM API PAYLOAD SENT] to {formatted_phone}: user_name='{customer_name}' | car_model='{agent_vars.get('car_model', '')}' | agent_vars={agent_vars}")
            response = requests.post(url, headers=cls.get_agent_headers(api_key), json=payload, timeout=10)

            # Self-healing fallback 1: If Sarvam rejects extra undeclared variables with 422, retry with user_name only
            if response.status_code == 422:
                logger.warning(f"⚠️ [SARVAM AGENT API 422]: App '{app_id}' rejected variables {agent_vars} (Body: {response.text}). Retrying with user_name only...")
                fallback_payload = dict(payload)
                fallback_payload["app_config"] = dict(payload["app_config"])
                fallback_payload["app_config"]["agent_variables"] = {"user_name": customer_name}
                response = requests.post(url, headers=cls.get_agent_headers(api_key), json=fallback_payload, timeout=10)

                # Self-healing fallback 2: If Sarvam STILL rejects with 422, retry with empty agent_variables {}
                if response.status_code == 422:
                    logger.warning(f"⚠️ [SARVAM AGENT API 422]: App '{app_id}' rejected user_name. Retrying with empty agent_variables...")
                    empty_payload = dict(payload)
                    empty_payload["app_config"] = dict(payload["app_config"])
                    empty_payload["app_config"]["agent_variables"] = {}
                    response = requests.post(url, headers=cls.get_agent_headers(api_key), json=empty_payload, timeout=10)

            logger.info(f"✅ [SARVAM AGENT API] Call initiated for {formatted_phone} via agent '{sarvam_agent.name if sarvam_agent else 'default'}'. Status: {response.status_code}")
            print(f"📥 [SARVAM AGENT API RESPONSE]: Status {response.status_code} | Body: {response.text}")
            return response.json()
        except Exception as e:
            logger.error(f"❌ [SARVAM AGENT API ERROR] Failed to trigger call for {formatted_phone}: {e}")
            return {"error": str(e)}

    @classmethod
    def list_interactions(cls, start_datetime: str = None, end_datetime: str = None, page_size: int = 100, sarvam_agent=None):
        """
        Lists all interactions from Sarvam AI Analytics API.
        Accepts optional sarvam_agent for multi-agent credential switching.
        """
        from datetime import datetime, timedelta
        org_id, workspace_id, app_id, api_key, _, _, _ = cls._creds(sarvam_agent)

        if not (org_id and workspace_id and app_id and api_key):
            return {"error": "Missing Sarvam credentials"}

        headers = {"X-API-Key": api_key}
        now = datetime.utcnow()
        start_dt = start_datetime or (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
        end_dt = end_datetime or now.strftime("%Y-%m-%dT23:59:59Z")

        url = f"{SARVAM_API_BASE_URL}/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/interactions"
        all_items = []
        offset = 0
        limit = min(page_size, 50)

        try:
            while True:
                params = {
                    "start_datetime": start_dt,
                    "end_datetime": end_dt,
                    "offset": offset,
                    "limit": limit
                }
                res = requests.get(url, headers=headers, params=params, timeout=15)
                if not res.content or res.status_code != 200:
                    break
                try:
                    data = res.json()
                except Exception:
                    logger.warning(f"⚠️ [SARVAM INTERACTIONS API]: Non-JSON response: {res.text[:300]}")
                    break

                items = data.get("items") or data.get("interactions") or data.get("data") or []
                if isinstance(data, list):
                    items = data

                all_items.extend(items)
                logger.info(f"📋 [SARVAM SYNC] Fetched {len(items)} interactions at offset {offset} (total so far: {len(all_items)})")

                total_avail = data.get("total", len(all_items)) if isinstance(data, dict) else len(all_items)
                next_uri = data.get("next_page_uri") if isinstance(data, dict) else None
                if not items or len(all_items) >= total_avail or not next_uri:
                    break
                offset += len(items)

            return {"items": all_items, "total": len(all_items)}
        except Exception as e:
            logger.error(f"❌ [SARVAM INTERACTIONS LIST ERROR]: {e}")
            return {"error": str(e)}

    @classmethod
    def sync_all_interactions(cls, days: int = 30, sarvam_agent=None):
        """
        Full sync: fetches ALL interactions from Sarvam Analytics API for the last N days,
        then fetches transcript + recording for each, and upserts into local SarvamCallRecord.
        Returns a summary dict with counts.
        Accepts optional sarvam_agent for multi-agent support.
        """
        from conversations.models import SarvamCallRecord
        from datetime import datetime, timedelta
        from dateutil import parser as dateutil_parser
        from django.db.models import Q

        logger.info(f"🔄 [SARVAM FULL SYNC] Starting sync for last {days} days...")
        now = datetime.utcnow()
        start_dt = (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
        end_dt = now.strftime("%Y-%m-%dT23:59:59Z")

        result = cls.list_interactions(start_datetime=start_dt, end_datetime=end_dt, sarvam_agent=sarvam_agent)
        if "error" in result:
            return {"error": result["error"], "synced": 0}

        interactions = result.get("items", [])
        logger.info(f"📋 [SARVAM FULL SYNC] Found {len(interactions)} total interactions to sync")

        synced = 0
        skipped = 0
        errors = 0

        for item in interactions:
            try:
                # Extract fields from Sarvam's interaction list response
                interaction_id = (
                    item.get("interaction_id")
                    or item.get("id")
                    or item.get("interactionId")
                )
                if not interaction_id:
                    skipped += 1
                    continue

                attempt_id_item = (
                    item.get("job_id")
                    or item.get("jobId")
                    or item.get("attempt_id")
                    or item.get("attemptId")
                )

                # Phone number: use user_contact first! (user_identifier is a SHA hash)
                phone_raw = (
                    item.get("user_contact")
                    or item.get("user_phone_number")
                    or item.get("phone_number")
                    or "unknown"
                )
                phone_digits = "".join(filter(str.isdigit, str(phone_raw)))

                duration = float(
                    item.get("duration_in_seconds")
                    or item.get("duration")
                    or item.get("duration_seconds")
                    or item.get("durationSeconds")
                    or 0
                )
                call_type_raw = (
                    item.get("call_type")
                    or item.get("callType")
                    or item.get("type")
                    or "Live Call"
                )
                call_type = "Test Call" if "test" in str(call_type_raw).lower() else "Live Call"

                agent_vars = item.get("agent_variables", {}) or {}
                call_sum = agent_vars.get("call_summary") or {}
                final_status = call_sum.get("final_status") if isinstance(call_sum, dict) and call_sum.get("final_status") else None

                status_raw = (
                    final_status
                    or item.get("status")
                    or item.get("completion_status")
                    or "COMPLETED"
                )

                start_time_str = item.get("attempted_at") or item.get("start_datetime") or item.get("start_time") or item.get("created_at")
                start_time_obj = None
                if start_time_str:
                    try:
                        start_time_obj = dateutil_parser.parse(start_time_str)
                    except Exception:
                        pass

                # Check if record already exists in local DB
                rec = SarvamCallRecord.objects.filter(interaction_id=interaction_id).first()
                if not rec and attempt_id_item:
                    rec = SarvamCallRecord.objects.filter(attempt_id=attempt_id_item).first()
                if not rec and phone_digits:
                    # When sarvam_agent is given, scope the match to that agent's records only
                    qs = SarvamCallRecord.objects.filter(phone_number__icontains=phone_digits[-10:])
                    if sarvam_agent:
                        qs = qs.filter(sarvam_agent=sarvam_agent)
                    rec = qs.filter(Q(interaction_id__isnull=True) | Q(interaction_id="")).order_by("-created_at").first()

                # Fetch recording URL only if missing on existing record
                audio_url = item.get("audio_url") or (rec.audio_url if rec else None)
                if not audio_url and time.time() > _SARVAM_RATE_LIMITED_UNTIL:
                    audio_url = cls.fetch_interaction_recording(interaction_id=interaction_id, sarvam_agent=sarvam_agent)
                if isinstance(audio_url, dict):
                    audio_url = (
                        audio_url.get("recording_url")
                        or audio_url.get("audio_url")
                        or audio_url.get("url")
                        or None
                    )

                # Fetch transcript only if missing on existing record
                transcript_text = (rec.transcript if rec and rec.transcript else "")
                if not transcript_text and time.time() > _SARVAM_RATE_LIMITED_UNTIL:
                    transcript_res = cls.fetch_interaction_transcript(interaction_id=interaction_id, sarvam_agent=sarvam_agent)
                    if isinstance(transcript_res, list):
                        transcript_text = "\n\n".join([
                            f"{t.get('role', 'Speaker').upper()}: {t.get('text', '') or t.get('content', '')}"
                            for t in transcript_res
                        ])
                    elif isinstance(transcript_res, dict):
                        if "messages" in transcript_res:
                            msgs = transcript_res.get("messages") or []
                            transcript_text = "\n\n".join([
                                f"{m.get('role', 'Speaker').upper()}: {m.get('content', '') or m.get('text', '')}"
                                for m in msgs
                            ])
                        else:
                            transcript_text = (
                                transcript_res.get("transcript")
                                or transcript_res.get("text")
                                or transcript_res.get("raw_text")
                                or ""
                            )

                if rec:
                    rec.interaction_id = interaction_id
                    rec.duration_seconds = duration if duration > 0 else rec.duration_seconds
                    if not rec.call_type or rec.call_type in ["Live Call", "Test Call"]:
                        rec.call_type = call_type
                    rec.status = status_raw
                    if isinstance(call_sum, dict) and call_sum:
                        if not rec.summary or len(str(rec.summary)) < len(str(call_sum)):
                            rec.summary = call_sum
                    if start_time_obj:
                        rec.start_time = start_time_obj
                    if transcript_text:
                        rec.transcript = transcript_text
                    if audio_url:
                        rec.audio_url = audio_url
                    if sarvam_agent and not rec.sarvam_agent:
                        rec.sarvam_agent = sarvam_agent
                    rec.save()
                else:
                    cand_name = "—"
                    if isinstance(call_sum, dict) and call_sum.get("candidate_name"):
                        cand_name = call_sum.get("candidate_name")
                    SarvamCallRecord.objects.create(
                        sarvam_agent=sarvam_agent,
                        interaction_id=interaction_id,
                        attempt_id=attempt_id_item,
                        phone_number=phone_raw,
                        candidate_name=cand_name,
                        call_type=call_type,
                        status=status_raw,
                        duration_seconds=duration,
                        summary=call_sum if isinstance(call_sum, dict) else {},
                        start_time=start_time_obj,
                        transcript=transcript_text,
                        audio_url=audio_url if isinstance(audio_url, str) else None,
                    )
                synced += 1
                logger.info(f"✅ [SARVAM SYNC] Synced {interaction_id} | Phone: {phone_raw} | Duration: {duration}s")

            except Exception as e:
                logger.error(f"❌ [SARVAM SYNC ERROR] interaction {item}: {e}")
                errors += 1

        logger.info(f"✅ [SARVAM FULL SYNC COMPLETE] synced={synced}, skipped={skipped}, errors={errors}")
        return {"synced": synced, "skipped": skipped, "errors": errors, "total": len(interactions)}

    @classmethod
    def fetch_interaction_transcript(cls, interaction_id: str = None, start_datetime: str = None, end_datetime: str = None, sarvam_agent=None):
        """
        Fetches interaction transcript using Sarvam AI Analytics API.
        Accepts optional sarvam_agent for multi-agent credential switching.
        """
        global _SARVAM_RATE_LIMITED_UNTIL
        if time.time() < _SARVAM_RATE_LIMITED_UNTIL:
            logger.warning(f"⏳ [SARVAM TRANSCRIPTS API] Paused requests due to rate limit backoff ({interaction_id})")
            return {"status": "paused", "message": "Rate limited backoff active"}

        org_id, workspace_id, app_id, api_key, _, _, _ = cls._creds(sarvam_agent)

        if not (org_id and workspace_id and app_id and api_key):
            logger.warning("⚠️ Missing Sarvam Org/Workspace/App credentials for Analytics API.")
            return {"error": "Missing Sarvam Analytics API credentials in .env"}

        headers = {
            "X-API-Key": api_key
        }

        # 1. If interaction_id is not supplied, fetch recent interactions first
        if not interaction_id:
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            start_dt = start_datetime or (now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
            end_dt = end_datetime or now.strftime("%Y-%m-%dT23:59:59Z")

            interactions_url = f"{SARVAM_API_BASE_URL}/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/interactions"
            try:
                res = requests.get(interactions_url, headers=headers, params={"start_datetime": start_dt, "end_datetime": end_dt}, timeout=10)
                if res.status_code in (429, 403):
                    _SARVAM_RATE_LIMITED_UNTIL = time.time() + 60
                    return {"status": "rate_limited", "message": "Rate limit / WAF block"}
                items = res.json().get("items", [])
                if items:
                    interaction_id = items[0].get("interaction_id")
                else:
                    return {"status": "empty", "message": "No interactions found in time window"}
            except Exception as e:
                logger.error(f"❌ [SARVAM ANALYTICS ERROR] List interactions failed: {e}")
                return {"error": str(e)}

        # 2. Fetch Transcript for the specific interaction_id
        transcript_url = f"{SARVAM_API_BASE_URL}/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/transcripts/{interaction_id}"
        try:
            transcript_res = requests.get(transcript_url, headers=headers, timeout=10)
            if transcript_res.status_code in (429, 403):
                _SARVAM_RATE_LIMITED_UNTIL = time.time() + 60
                logger.warning(f"⚠️ [SARVAM TRANSCRIPTS API]: Status {transcript_res.status_code} for {interaction_id} — Backing off API requests for 60s.")
                return {"status": "rate_limited", "message": "Rate limit / WAF block"}
            if not transcript_res.content:
                logger.warning(f"⚠️ [SARVAM TRANSCRIPTS API]: Empty body for {interaction_id}")
                return {"status": "empty", "message": "No transcript content returned"}
            try:
                return transcript_res.json()
            except Exception:
                logger.warning(f"⚠️ [SARVAM TRANSCRIPTS API]: Non-JSON response for {interaction_id}: {transcript_res.text[:200]}")
                return {"raw_text": transcript_res.text}
        except Exception as e:
            logger.error(f"❌ [SARVAM ANALYTICS ERROR] Fetch transcript failed: {e}")
            return {"error": str(e)}

    @classmethod
    def fetch_interaction_recording(cls, interaction_id: str, sarvam_agent=None):
        """
        Fetches interaction audio recording using Sarvam AI Analytics Recordings API.
        Accepts optional sarvam_agent for multi-agent credential switching.
        """
        global _SARVAM_RATE_LIMITED_UNTIL
        if time.time() < _SARVAM_RATE_LIMITED_UNTIL:
            logger.warning(f"⏳ [SARVAM RECORDINGS API] Paused requests due to rate limit backoff ({interaction_id})")
            return None

        org_id, workspace_id, app_id, api_key, _, _, _ = cls._creds(sarvam_agent)

        if not (org_id and workspace_id and app_id and api_key and interaction_id):
            return None

        headers = {"X-API-Key": api_key}
        url = f"{SARVAM_API_BASE_URL}/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/recordings/{interaction_id}"
        try:
            logger.info(f"🎙️ [SARVAM RECORDINGS API] Fetching audio recording for: {interaction_id}")

            # First attempt WITHOUT following redirects so we can capture the Location header
            res = requests.get(url, headers=headers, timeout=10, allow_redirects=False)

            if res.status_code in (429, 403):
                _SARVAM_RATE_LIMITED_UNTIL = time.time() + 60
                logger.warning(f"⚠️ [SARVAM RECORDINGS API]: Status {res.status_code} for {interaction_id} — Backing off API requests for 60s.")
                return None

            # Case 1: Redirect → Location header IS the audio file URL
            if res.status_code in (301, 302, 303, 307, 308):
                redirect_url = res.headers.get("Location")
                if redirect_url:
                    logger.info(f"✅ [SARVAM RECORDINGS API] Got redirect URL: {redirect_url}")
                    return redirect_url

            # Follow redirects for the actual content response
            if res.status_code in (301, 302, 303, 307, 308):
                res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)

            if res.status_code == 200:
                content_type = res.headers.get("Content-Type", "")

                # Case 2: Empty body (no content)
                if not res.content:
                    logger.warning(f"⚠️ [SARVAM RECORDINGS API]: Empty body for {interaction_id}")
                    return None

                # Case 3: Audio/binary content returned directly → return the final URL
                if "audio" in content_type or "octet-stream" in content_type or "binary" in content_type:
                    final_url = res.url  # The URL after redirects
                    logger.info(f"✅ [SARVAM RECORDINGS API] Audio binary returned, final URL: {final_url}")
                    return final_url

                # Case 4: JSON response with a URL field
                try:
                    data = res.json()
                    print(f"✅ [SARVAM RECORDINGS API RESPONSE]: {data}")
                    if isinstance(data, dict):
                        audio_url = (
                            data.get("recording_url")
                            or data.get("audio_url")
                            or data.get("url")
                            or data.get("download_url")
                            or data.get("media_url")
                            or data.get("file_url")
                        )
                        return audio_url or data
                    return data
                except Exception:
                    # Response body exists but is not JSON — try to use the final URL
                    logger.warning(f"⚠️ [SARVAM RECORDINGS API]: Non-JSON body for {interaction_id}, using response URL")
                    return res.url if res.url != url else None
            else:
                logger.warning(f"⚠️ [SARVAM RECORDINGS API]: Status {res.status_code} for {interaction_id} — Body: {res.text[:200]}")
        except Exception as e:
            logger.error(f"❌ [SARVAM RECORDINGS API ERROR]: {e}")
        return None
