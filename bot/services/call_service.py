# # ============================================================
# #  bot/services/call_service.py
# #  Initiates voice bot calls via WebSocket
# # ============================================================

# import asyncio
# import logging
# from urllib.parse import urlencode

# import websockets

# from django.conf import settings

# logger = logging.getLogger(__name__)

# # ── Config (can be overridden in settings.py) ─────────────
# VOICE_BOT_WS_URL = getattr(
#     settings,
#     "VOICE_BOT_WS_URL",
#     "wss://nonesthetically-affectional-janel.ngrok-free.dev/ws/voice-bot/",
# )
# VOICE_BOT_AGENT_ID = getattr(
#     settings,
#     "VOICE_BOT_AGENT_ID",
#     "ed0ffb87-e5d0-45b6-8fb5-95c736d728a0",
# )


# async def _connect_and_initiate(phone: str) -> dict:
#     """
#     Open a WebSocket to the voice-bot service.
#     The service will initiate a real phone call to `phone`.
#     We keep the connection open briefly to confirm it was accepted,
#     then close (the voice bot maintains the call independently).
#     """
#     params = urlencode({"agent_id": VOICE_BOT_AGENT_ID, "phone": phone})
#     ws_url = f"{VOICE_BOT_WS_URL}?{params}"

#     logger.info("[VoiceBot] Connecting to %s", ws_url)

#     try:
#         async with websockets.connect(
#             ws_url,
#             additional_headers={"Origin": "https://dashboard.local"},
#             open_timeout=10,
#             close_timeout=5,
#         ) as ws:
#             logger.info("[VoiceBot] Connected — call initiated to %s", phone)

#             # Wait briefly for any acknowledgement from the voice bot
#             try:
#                 ack = await asyncio.wait_for(ws.recv(), timeout=5)
#                 logger.info("[VoiceBot] Ack received: %s", ack)
#             except asyncio.TimeoutError:
#                 logger.info("[VoiceBot] No ack within 5s (that's OK, call may be in progress)")

#             return {"status": "call_initiated", "phone": phone}

#     except websockets.exceptions.InvalidStatusCode as e:
#         logger.error("[VoiceBot] Connection rejected: %s", e)
#         return {"status": "error", "detail": f"Connection rejected: {e.status_code}"}
#     except Exception as e:
#         logger.error("[VoiceBot] Connection failed: %s", e)
#         return {"status": "error", "detail": str(e)}


# def initiate_voice_call(phone: str) -> dict:
#     """
#     Synchronous wrapper — safe to call from a Django view.
#     """
#     return asyncio.run(_connect_and_initiate(phone))



































# ============================================================
#  bot/services/call_service.py
# ============================================================

import asyncio
import logging
from urllib.parse import urlencode

import websockets
import websockets.exceptions

from django.conf import settings

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────
VOICE_BOT_WS_URL = getattr(
    settings,
    "VOICE_BOT_WS_URL",
    "wss://insurancebot-b3aha4cmfnbghza7.centralindia-01.azurewebsites.net/ws/voice-bot/",
)
VOICE_BOT_AGENT_ID = getattr(
    settings,
    "VOICE_BOT_AGENT_ID",
    "3db2a820-2745-47b9-aa8b-f42c99f727e4",
)


async def _connect_and_initiate(phone: str) -> dict:
    params = urlencode({"agent_id": VOICE_BOT_AGENT_ID, "phone": phone})
    ws_url = f"{VOICE_BOT_WS_URL}?{params}"

    logger.info("[VoiceBot] Connecting to %s", ws_url)

    try:
        async with websockets.connect(
            ws_url,
            additional_headers={"Origin": "https://dashboard.local"},
            open_timeout=10,
            close_timeout=5,
        ) as ws:
            logger.info("[VoiceBot] Connected — call initiated to %s", phone)

            try:
                ack = await asyncio.wait_for(ws.recv(), timeout=5)
                logger.info("[VoiceBot] Ack: %s", ack)
            except asyncio.TimeoutError:
                logger.info("[VoiceBot] No ack within 5s — call may still be in progress")

            return {"status": "call_initiated", "phone": phone}

    # ── HTTP 4xx/5xx during WebSocket handshake ────────────
    # websockets >= 10: RejectHandshake / InvalidHandshake
    # websockets <  10: InvalidStatusCode
    except websockets.exceptions.InvalidHandshake as e:
        status_code = getattr(e, "status_code", None) or getattr(e, "code", "unknown")
        logger.error("[VoiceBot] Handshake rejected — HTTP %s at %s", status_code, ws_url)

        if status_code == 404:
            detail = (
                f"WebSocket path not found (404). "
                f"Check that your voice bot server has a route registered at: {VOICE_BOT_WS_URL}"
            )
        elif status_code == 403:
            detail = "WebSocket connection forbidden (403). Check Origin/auth headers."
        elif status_code == 502:
            detail = "Bad gateway (502). The voice bot service behind ngrok may not be running."
        else:
            detail = f"Handshake failed with HTTP {status_code}."

        return {"status": "error", "detail": detail}

    except websockets.exceptions.WebSocketException as e:
        logger.error("[VoiceBot] WebSocket error: %s", e)
        return {"status": "error", "detail": f"WebSocket error: {e}"}

    except OSError as e:
        # DNS / TCP connection failure
        logger.error("[VoiceBot] Connection failed (network): %s", e)
        return {"status": "error", "detail": f"Could not reach voice bot server: {e}"}

    except Exception as e:
        logger.exception("[VoiceBot] Unexpected error")
        return {"status": "error", "detail": str(e)}


def initiate_voice_call(phone: str) -> dict:
    """
    Synchronous wrapper safe to call from a standard Django (WSGI) view.

    Uses get_event_loop() instead of asyncio.run() to avoid
    'This event loop is already running' errors under Daphne / Uvicorn.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Async context (Daphne/Uvicorn) — create a new loop in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _connect_and_initiate(phone))
                return future.result(timeout=20)
        else:
            return loop.run_until_complete(_connect_and_initiate(phone))
    except Exception as e:
        logger.exception("[VoiceBot] initiate_voice_call failed")
        return {"status": "error", "detail": str(e)}