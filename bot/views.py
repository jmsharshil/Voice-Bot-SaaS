# ============================================================
#  bot/views.py
# ============================================================
 
from datetime import date, timedelta
import os
import re
import time
import json
import openpyxl
from datetime import datetime, timedelta
 
import pandas as pd
from django.core.cache import cache
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import io

from bot.models import Customer, ChatMessage, UploadedFile, UploadBatch, CampaignStatus, Campaign
from bot.services.whatsapp_service import send_whatsapp_message
from bot.services.renewal_service import run_renewal, run_new_insurance, run_all
from bot.services.expiry_service import get_expiring_customers, get_new_insurance_customers
import requests
import uuid
 
# ============================================================
#  CONSTANTS & CONFIG
# ============================================================
 
UPLOAD_PROGRESS_KEY = "upload_progress"

# Session timeout in seconds — if the last bot message is older than
# this, the conversation resets so the user starts fresh.
SESSION_TIMEOUT_SECONDS = 60
 
CLOSING_KEYWORDS = {
    "ok", "okay", "okk", "okkk",
    "thank you", "thanks", "thankyou",
    "bye", "bye bye", "goodbye", "thx", "ty",
}
 
POSITIVE_KEYWORDS = {
    "yes", "yeah", "yup", "sure", "haan", "ha",
    "renew", "please renew", "do it", "go ahead", "proceed",
}
 
NEGATIVE_KEYWORDS = {
    "no", "nope", "not now", "later", "maybe later",
    "don't", "do not", "not interested", "nahi", "na",
}
 
# ✅ NEW: greeting keywords to activate inbound bot
GREETING_KEYWORDS = {
    "hi", "hello", "hey", "hii", "helo", "hlw",
    "hye", "start", "help", "namaskar", "namaste",
}
 
# ── Coverage options per vehicle type ──────────────────────
COVERAGE_OPTIONS = {
    "Car": [
        ("Third Party",       2094),
        ("Comprehensive",     8500),
        ("Zero Depreciation", 12000),
    ],
    "Bike": [
        ("Third Party",       714),
        ("Comprehensive",     2500),
        ("Long Term 2yr TP",  1200),
        ("Long Term 3yr TP",  1600),
    ],
    "Commercial": [
        ("Third Party",          4000),
        ("Comprehensive",        15000),
        ("Goods Carrying",       18000),
        ("Passenger Carrying",   20000),
    ],
    "Auto": [
        ("Third Party",    1500),
        ("Comprehensive",  4500),
    ],
    "Tractor": [
        ("Third Party Only",             1500),
        ("Comprehensive + Farm Equip",   7000),
        ("Fire & Theft Only",            3000),
    ],
}
 
# ── Add-on options per vehicle type (name, extra premium) ──
ADDON_OPTIONS = {
    "Car": [
        ("Zero Depreciation",  1500),
        ("Roadside Assistance", 500),
        ("Engine Protection",   800),
        ("Return to Invoice",   700),
        ("Key Replacement",     300),
        ("Consumables Cover",   400),
    ],
    "Bike": [
        ("Zero Depreciation",   500),
        ("Roadside Assistance", 200),
        ("Personal Accident",   300),
    ],
    "Commercial": [
        ("Goods in Transit",  1500),
        ("Driver PA Cover",    500),
        ("Cleaner/Helper Cover", 300),
    ],
    "Auto": [
        ("Passenger Cover (up to 3)", 400),
        ("Driver PA Cover",           300),
    ],
    "Tractor": [
        ("Driver PA Cover",          300),
        ("Trolley/Attachment Cover", 600),
    ],
}
 
PAYMENT_LINK = "https://your-payment-link.com"
 
 
# ============================================================
#  HELPERS
# ============================================================
 
def _set_progress(sent: int, total: int, active: bool) -> None:
    cache.set(UPLOAD_PROGRESS_KEY, {"sent": sent, "total": total, "active": active}, timeout=3600)
 
 
def _save_msg(customer: Customer, message: str, sender: str) -> None:
    ChatMessage.objects.create(customer=customer, message=message, sender=sender)
 
 
def _send_and_save(customer: Customer, reply: str) -> None:
    send_whatsapp_message(customer.phone, reply)
    _save_msg(customer, reply, "bot")
 
 
def _has_any(text: str, keyword_set: set) -> bool:
    return any(word in text for word in keyword_set)
 
 
def _parse_expiry(raw) -> "date | None":
    if pd.isnull(raw):
        return None
    try:
        parsed = pd.to_datetime(raw, errors="coerce")
        return parsed.date() if pd.notnull(parsed) else None
    except Exception:
        return None
 
 
def _validate_vehicle_number(text: str) -> bool:
    pattern = r'^[A-Z]{2}[\s\-]?\d{2}[\s\-]?[A-Z]{1,2}[\s\-]?\d{4}$'
    return bool(re.match(pattern, text.upper().strip()))
 
 
def _build_coverage_menu(vehicle_type: str) -> str:
    options = COVERAGE_OPTIONS.get(vehicle_type, [])
    lines = [f"{i+1}️⃣ {name}  (₹{price:,}/yr)" for i, (name, price) in enumerate(options)]
    return "\n".join(lines)
 
 
def _build_addon_menu(vehicle_type: str) -> str:
    options = ADDON_OPTIONS.get(vehicle_type, [])
    lines = [f"{i+1}️⃣ {name}  (+₹{price:,})" for i, (name, price) in enumerate(options)]
    lines.append(f"{len(options)+1}️⃣ No add-ons")
    return "\n".join(lines)
 
 
def _calculate_premium(vehicle_type: str, coverage_index: int, addon_indices: list) -> tuple:
    coverages = COVERAGE_OPTIONS.get(vehicle_type, [])
    addons    = ADDON_OPTIONS.get(vehicle_type, [])
 
    coverage_name, base_premium = coverages[coverage_index]
 
    selected_addon_names = []
    total_addon_premium  = 0
 
    for idx in addon_indices:
        if 0 <= idx < len(addons):
            name, price = addons[idx]
            selected_addon_names.append(name)
            total_addon_premium += price
 
    total     = base_premium + total_addon_premium
    addon_str = ", ".join(selected_addon_names) if selected_addon_names else "None"
 
    return coverage_name, addon_str, total


def _check_session_timeout(customer):
    """Check if the customer's conversation has timed out.
    If the last bot message is older than SESSION_TIMEOUT_SECONDS,
    reset the session so the user starts fresh.
    Returns True if session was reset, False otherwise.
    """
    ACTIVE_STATES = {
        "ask_service_type", "ask_vehicle_category",
        "ask_vehicle_other", "ask_vehicle_details", "ask_vehicle_model",
        "ask_coverage", "ask_addons", "show_quote", "payment_sent",
        "ask_reminder",
    }

    if customer.conversation_state not in ACTIVE_STATES:
        return False

    # Find the last bot message for this customer
    last_bot_msg = (
        ChatMessage.objects
        .filter(customer=customer, sender="bot")
        .order_by("-timestamp")
        .first()
    )

    if not last_bot_msg:
        return False

    elapsed = (timezone.now() - last_bot_msg.timestamp).total_seconds()

    if elapsed > SESSION_TIMEOUT_SECONDS:
        # Reset: outbound → "initial", inbound → "inactive"
        if customer.source == "outbound":
            customer.conversation_state = "initial"
        else:
            customer.conversation_state = "inactive"

        # Clear mid-conversation selections
        customer.selected_coverage = None
        customer.selected_addons   = None
        customer.quoted_premium    = None
        customer.save()

        print(f"[timeout] Session expired for {customer.phone} "
              f"(idle {elapsed:.0f}s > {SESSION_TIMEOUT_SECONDS}s) → reset to '{customer.conversation_state}'")
        return True

    return False
 
 
# ============================================================
#  WHATSAPP WEBHOOK — STATE MACHINE
# ============================================================
 
@api_view(["POST"])
def whatsapp_webhook(request):
    data = request.data
 
    try:
        if data.get("event") != "messages.received":
            return Response({"status": "ignored"})
 
        message_data = data.get("data", {}).get("messages", {})
        phone        = message_data.get("key", {}).get("cleanedSenderPn")
        raw_text     = message_data.get("messageBody", "")
 
        if not phone or not raw_text:
            return Response({"status": "no data"})
 
        text = raw_text.lower().strip()
        print(f"[webhook] phone={phone}  text={text!r}")

        # ── Normalize phone — strip 91 prefix if 12 digits ──
        if phone and str(phone).startswith("91") and len(str(phone)) == 12:
            phone = str(phone)[2:]
            print(f"[webhook] normalized phone: {phone}")
 
        # ── Smart routing: decide which customer record gets this msg ──
        inbound_cust  = Customer.objects.filter(phone=phone, source="inbound").first()
        outbound_cust = Customer.objects.filter(phone=phone, source="outbound").first()
 
        # ── Session timeout: auto-reset stale conversations BEFORE routing ──
        if inbound_cust:
            _check_session_timeout(inbound_cust)
            inbound_cust.refresh_from_db()
        if outbound_cust:
            _check_session_timeout(outbound_cust)
            outbound_cust.refresh_from_db()

        # Active = conversation is in progress (not idle)
        ACTIVE_STATES = {
            "initial", "ask_service_type", "ask_vehicle_category",
            "ask_vehicle_other", "ask_vehicle_details", "ask_vehicle_model",
            "ask_coverage", "ask_addons", "show_quote", "payment_sent",
            "ask_reminder",
        }
 
        outbound_active = outbound_cust and outbound_cust.conversation_state in ACTIVE_STATES
        inbound_active  = inbound_cust  and inbound_cust.conversation_state  in ACTIVE_STATES
 
        if outbound_active:
            # Outbound customer is mid-conversation → route reply there
            customer = outbound_cust
        elif inbound_active:
            # Inbound customer is mid-conversation → route there
            customer = inbound_cust
        elif inbound_cust:
            # Both idle → prefer inbound for new conversations
            customer = inbound_cust
        elif outbound_cust:
            # Only outbound exists
            customer = outbound_cust
        else:
            # No customer at all → create inbound if greeting
            if _has_any(text, GREETING_KEYWORDS):
                customer = Customer.objects.create(
                    phone=phone,
                    name="User",
                    source="inbound",
                    conversation_state="inactive",
                )
                print(f"[webhook] New inbound customer created: {phone}")
            else:
                return Response({"status": "user not found"})
 
        _save_msg(customer, text, "user")


        # ── Closing short-circuit ──────────────────────────────
        if _has_any(text, CLOSING_KEYWORDS):
            _send_and_save(customer, "You're welcome 😊Say *Hi* anytime to start a new conversation 👋")
            customer.conversation_state = "inactive"   # session reset
            customer.save()
            return Response({"status": "closed"})
 
        state    = customer.conversation_state
        positive = _has_any(text, POSITIVE_KEYWORDS)
        negative = _has_any(text, NEGATIVE_KEYWORDS)
        vtype    = customer.vehicle_type
 
        # ══════════════════════════════════════════════════════
        # ✅ NEW INBOUND STATES (added above existing flow)
        # ══════════════════════════════════════════════════════
 
        # ==================================================
        # STATE: inactive
        # User sends hi/hello → activate bot
        # ==================================================
        if state == "inactive":
            if _has_any(text, GREETING_KEYWORDS):
                reply = (
                    "Hello! 👋 Welcome to *Vehicle Insurance* 🚗🏍️\n\n"
                    "I'm here to help you with insurance.\n\n"
                    "What are you looking for?\n"
                    "1️⃣ New Insurance\n"
                    "2️⃣ Renewal"
                )
                customer.conversation_state = "ask_service_type"
            else:
                reply = (
                    "Hello! 👋 Please say *Hi* to get started 😊"
                )
 
        # ==================================================
        # STATE: ask_service_type
        # User picks New Insurance (1) or Renewal (2)
        # ==================================================
        elif state == "ask_service_type":
            if text == "1":
                customer.customer_type = "new"
                reply = (
                    "Great! 😊 Let's get you insured.\n\n"
                    "What type of vehicle do you have?\n"
                    "1️⃣ Two Wheeler  (Bike / Scooter)\n"
                    "2️⃣ Four Wheeler (Car / SUV / MUV)\n"
                    "3️⃣ Other        (Commercial / Auto / Tractor)"
                )
                customer.conversation_state = "ask_vehicle_category"
 
            elif text == "2":
                customer.customer_type = "renewal"
                reply = (
                    "Sure! Let's renew your policy 😊\n\n"
                    "What type of vehicle do you have?\n"
                    "1️⃣ Two Wheeler  (Bike / Scooter)\n"
                    "2️⃣ Four Wheeler (Car / SUV / MUV)\n"
                    "3️⃣ Other        (Commercial / Auto / Tractor)"
                )
                customer.conversation_state = "ask_vehicle_category"
 
            else:
                reply = (
                    "Please reply with *1* or *2* 😊\n\n"
                    "1️⃣ New Insurance\n"
                    "2️⃣ Renewal"
                )
 
        # ==================================================
        # STATE: ask_vehicle_category
        # 1 = Two Wheeler → Bike
        # 2 = Four Wheeler → Car
        # 3 = Other → ask sub-type
        # ==================================================
        elif state == "ask_vehicle_category":
            if text == "1":
                customer.vehicle_type = "Bike"
                reply = (
                    "Got it! 🏍️\n\n"
                    "Please share your *vehicle registration number*:\n\n"
                    "Example: *GJ05AB1234*"
                )
                customer.conversation_state = "ask_vehicle_details"
 
            elif text == "2":
                customer.vehicle_type = "Car"
                reply = (
                    "Got it! 🚗\n\n"
                    "Please share your *vehicle registration number*:\n\n"
                    "Example: *GJ01AB1234*"
                )
                customer.conversation_state = "ask_vehicle_details"
 
            elif text == "3":
                reply = (
                    "Please select your vehicle type:\n\n"
                    "1️⃣ Commercial Vehicle (Truck / Bus / Tempo)\n"
                    "2️⃣ Auto Rickshaw / E-Rickshaw\n"
                    "3️⃣ Tractor / Farm Equipment"
                )
                customer.conversation_state = "ask_vehicle_other"
 
            else:
                reply = (
                    "Please reply with *1*, *2* or *3* 😊\n\n"
                    "1️⃣ Two Wheeler\n"
                    "2️⃣ Four Wheeler\n"
                    "3️⃣ Other"
                )
 
        # ==================================================
        # STATE: ask_vehicle_other
        # Sub-menu for Commercial / Auto / Tractor
        # ==================================================
        elif state == "ask_vehicle_other":
            if text == "1":
                customer.vehicle_type = "Commercial"
                emoji = "🚛"
            elif text == "2":
                customer.vehicle_type = "Auto"
                emoji = "🛺"
            elif text == "3":
                customer.vehicle_type = "Tractor"
                emoji = "🚜"
            else:
                reply = (
                    "Please reply with *1*, *2* or *3* 😊\n\n"
                    "1️⃣ Commercial Vehicle\n"
                    "2️⃣ Auto Rickshaw / E-Rickshaw\n"
                    "3️⃣ Tractor / Farm Equipment"
                )
                customer.save()
                _send_and_save(customer, reply)
                return Response({"status": "received"})
 
            reply = (
                f"Got it! {emoji}\n\n"
                "Please share your *vehicle registration number*:\n\n"
                "Example: *GJ03AB1234*"
            )
            customer.conversation_state = "ask_vehicle_details"
 
        # ==================================================
        # STATE: ask_vehicle_details
        # Step 1 — Ask vehicle number only
        # ==================================================
        elif state == "ask_vehicle_details":
            vehicle_number = raw_text.strip().upper()
 
            if _validate_vehicle_number(vehicle_number):
                customer.vehicle_number = vehicle_number
                customer.policy_type    = customer.vehicle_type  # backward compat
 
                reply = (
                    f"Got it! ✅ *{vehicle_number}*\n\n"
                    f"Now please share your *vehicle model*:\n\n"
                    f"Example: *Honda Activa* / *Maruti Swift* / *Tata Ace*"
                )
                customer.conversation_state = "ask_vehicle_model"
 
            else:
                reply = (
                    "Please enter a valid vehicle registration number 😊\n\n"
                    "Example: *GJ01AB1234*"
                )
 
        # ==================================================
        # STATE: ask_vehicle_model
        # Step 2 — Ask vehicle model
        # ==================================================
        elif state == "ask_vehicle_model":
            vehicle_model = raw_text.strip()
 
            if len(vehicle_model) >= 2:
                customer.vehicle_model = vehicle_model
 
                vtype = customer.vehicle_type
                menu  = _build_coverage_menu(vtype)
 
                reply = (
                    f"Perfect! 🚗\n\n"
                    f"*Vehicle No* : {customer.vehicle_number}\n"
                    f"*Model*      : {vehicle_model}\n"
                    f"*Type*       : {vtype}\n\n"
                    f"Now choose your coverage:\n\n"
                    f"{menu}"
                )
                customer.conversation_state = "ask_coverage"
 
            else:
                reply = (
                    "Please enter your vehicle model 😊\n\n"
                    "Example: *Honda Activa* / *Maruti Swift*"
                )
 
        # ══════════════════════════════════════════════════════
        # EXISTING OUTBOUND FLOW — UNCHANGED BELOW THIS LINE
        # ══════════════════════════════════════════════════════
 
        # ==================================================
        # STATE: initial
        # Outbound user replies to bot's first message
        # ==================================================
        elif state == "initial":
            if positive:
                menu  = _build_coverage_menu(vtype)
                reply = (
                    f"Great! Let's get started 😊\n\n"
                    f"Choose your coverage for *{customer.vehicle_number or vtype}*:\n\n"
                    f"{menu}"
                )
                customer.conversation_state = "ask_coverage"
 
            elif negative:
                if customer.customer_type == "renewal":
                    reply = (
                        f"No worries 😊\n\n"
                        f"Your policy expires on *{customer.expiry_date}*.\n"
                        f"Should I remind you 3 days before expiry? (Yes / No)"
                    )
                else:
                    reply = (
                        "No worries 😊\n\n"
                        "But remember — driving uninsured is illegal ⚠️\n\n"
                        "Should I follow up with you tomorrow? (Yes / No)"
                    )
                customer.conversation_state = "ask_reminder"
 
            else:
                if customer.customer_type == "renewal":
                    reply = (
                        f"I'm here to help 😊\n\n"
                        f"Your *{vtype}* policy expires on *{customer.expiry_date}*.\n"
                        f"Would you like to renew it? (Yes / No)"
                    )
                else:
                    reply = (
                        f"I'm here to help 😊\n\n"
                        f"Would you like to get insurance for your "
                        f"*{vtype}* ({customer.vehicle_number})? (Yes / No)"
                    )
 
        # ==================================================
        # STATE: ask_coverage
        # ==================================================
        elif state == "ask_coverage":
            coverages = COVERAGE_OPTIONS.get(vtype, [])
 
            if text.isdigit() and 1 <= int(text) <= len(coverages):
                idx = int(text) - 1
                customer.selected_coverage = str(idx)
 
                menu  = _build_addon_menu(vtype)
                reply = (
                    f"Good choice! 👍\n\n"
                    f"Now select add-ons for your *{vtype}*:\n"
                    f"(Send numbers separated by space, e.g. *1 3*)\n\n"
                    f"{menu}"
                )
                customer.conversation_state = "ask_addons"
 
            else:
                menu  = _build_coverage_menu(vtype)
                reply = (
                    f"Please reply with a number 1–{len(coverages)} 😊\n\n"
                    f"{menu}"
                )
 
        # ==================================================
        # STATE: ask_addons
        # ==================================================
        elif state == "ask_addons":
            addons     = ADDON_OPTIONS.get(vtype, [])
            no_addon_n = len(addons) + 1
            parts      = text.split()
            valid      = True
            addon_indices = []
 
            for p in parts:
                if p.isdigit():
                    n = int(p)
                    if n == no_addon_n:
                        addon_indices = []
                        break
                    elif 1 <= n <= len(addons):
                        addon_indices.append(n - 1)
                    else:
                        valid = False
                        break
                else:
                    valid = False
                    break
 
            if not valid:
                menu  = _build_addon_menu(vtype)
                reply = (
                    f"Please send valid numbers 😊\n\n"
                    f"{menu}"
                )
            else:
                cov_idx = int(customer.selected_coverage or "0")
                coverage_name, addon_str, total = _calculate_premium(vtype, cov_idx, addon_indices)
 
                customer.selected_addons = addon_str
                customer.quoted_premium  = total
 
                action = "renew" if customer.customer_type == "renewal" else "get insured"
 
                reply = (
                    f"Here's your quote 📋\n"
                    f"──────────────────────────\n"
                    f"Name       : {customer.name}\n"
                    f"Vehicle    : {customer.vehicle_number or 'N/A'}\n"
                    f"Model      : {customer.vehicle_model or 'N/A'}\n"
                    f"Type       : {vtype}\n"
                    f"Coverage   : {coverage_name}\n"
                    f"Add-ons    : {addon_str}\n"
                    f"Premium    : ₹{total:,}/year\n"
                    f"──────────────────────────\n\n"
                    f"Shall I proceed to {action}? (Yes / No)"
                )
                customer.conversation_state = "show_quote"
 
        # ==================================================
        # STATE: show_quote
        # ==================================================
        elif state == "show_quote":
            if positive:
                reply = (
                    f"Perfect! 🎉\n\n"
                    f"Click below to pay securely:\n"
                    f"🔗 {PAYMENT_LINK}\n\n"
                    f"Your policy will be issued within minutes "
                    f"after payment ✅\n\n"
                    f"Please reply *Done* once payment is complete."
                )
                customer.conversation_state = "payment_sent"
 
            elif negative:
                menu  = _build_coverage_menu(vtype)
                reply = (
                    f"No problem 😊 Let's pick again.\n\n"
                    f"Choose your coverage for *{customer.vehicle_number or vtype}*:\n\n"
                    f"{menu}"
                )
                customer.conversation_state = "ask_coverage"
 
            else:
                reply = "Please reply *Yes* to proceed or *No* to change your plan 😊"
 
        # ==================================================
        # STATE: payment_sent
        # ==================================================
        elif state == "payment_sent":
            payment_done = any(w in text for w in [
                "done", "paid", "payment done", "completed",
                "complete", "yes", "sent"
            ])
 
            if payment_done:
                if customer.customer_type == "renewal":
                    action_msg = f"Your *{vtype}* insurance has been *renewed* ✅"
                else:
                    action_msg = f"Your *{vtype}* is now *insured* ✅"
 
                reply = (
                    f"🎉 Congratulations *{customer.name}*!\n\n"
                    f"{action_msg}\n\n"
                    f"Policy document will be sent to your "
                    f"registered email/WhatsApp shortly 📧\n\n"
                    f"Thank you for choosing us! 😊\n\n"
                    f"Say *Hi* anytime if you need help again 👋"
                )
                customer.conversation_state = "inactive"   # session reset
 
            else:
                reply = (
                    f"Please complete the payment here:\n"
                    f"🔗 {PAYMENT_LINK}\n\n"
                    f"Reply *Done* once payment is complete 😊"
                )
 
        # ==================================================
        # STATE: ask_reminder
        # ==================================================
        elif state == "ask_reminder":
            if positive:
                if customer.customer_type == "renewal":
                    reply = (
                        f"Done! ✅ I'll remind you 3 days before "
                        f"your policy expires on *{customer.expiry_date}* 😊"
                    )
                else:
                    reply = (
                        "Done! ✅ I'll follow up with you tomorrow 😊\n\n"
                        "Remember — getting insured takes just 2 minutes! ⚡"
                    )
                customer.conversation_state = "inactive"   # session reset
 
            elif negative:
                reply = (
                    "Alright 😊\n\n"
                    "Feel free to reach out whenever you're ready.\n\n"
                    "Say *Hi* anytime to start again! 👋"
                )
                customer.conversation_state = "inactive"   # session reset
 
            else:
                reply = "Please reply *Yes* or *No* 😊"
 
        # ==================================================
        # STATE: policy_issued / done / closed — fallback
        # ==================================================
        else:
            reply = (
                "I'm here if you need any help 😊\n\n"
                "You can always reach out for insurance queries!"
            )
 
        customer.save()
        _send_and_save(customer, reply)
 
    except Exception as e:
        print(f"[webhook] ERROR: {e}")
        import traceback; traceback.print_exc()
 
    return Response({"status": "received"})
 
 
# ============================================================
#  TEST / TRIGGER ENDPOINTS
# ============================================================
 
@api_view(["GET"])
def test_send_message(request):
    phone   = "919104142402"
    message = "Hello 👋 This is a test message from Django bot"
    result  = send_whatsapp_message(phone, message)
    return Response({"status": "message sent", "response": result})
 
 
@api_view(["GET"])
def run_renewal_api(request):
    run_renewal()
    return Response({"status": "renewal messages sent"})
 
 
@api_view(["GET"])
def run_new_insurance_api(request):
    run_new_insurance()
    return Response({"status": "new insurance messages sent"})
 
 
@api_view(["GET"])
def run_all_campaigns_api(request):
    run_all()
    return Response({"status": "all campaigns triggered"})

@api_view(["GET"])
def run_expired_api(request):
    from bot.services.renewal_service import run_expired
    run_expired()
    return Response({"status": "expired reminders sent"})
 
 
# ============================================================
#  FILE UPLOAD
# ============================================================
 
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def upload_file(request):
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "No file uploaded"}, status=400)
 
    obj       = UploadedFile.objects.create(file=file)
    file_path = obj.file.path
    ext       = os.path.splitext(file_path)[1].lower()
 
    customers_data = []
 
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
        print("[upload] Columns:", df.columns.tolist())
 
        for _, row in df.iterrows():
            phone = str(row.get("phone") or "").strip()
            if not phone:
                continue
 
            raw_ctype     = str(row.get("customer_type") or "renewal").strip().lower()
            customer_type = "new" if raw_ctype == "new" else "renewal"
 
            raw_vtype    = str(row.get("vehicle_type") or "Car").strip().title()
            valid_types  = {"Car", "Bike", "Commercial", "Auto", "Tractor"}
            vehicle_type = raw_vtype if raw_vtype in valid_types else "Car"
 
            customers_data.append({
                "name":           str(row.get("name") or "Customer").strip(),
                "phone":          phone,
                "customer_type":  customer_type,
                "vehicle_type":   vehicle_type,
                "vehicle_number": str(row.get("vehicle_number") or "").strip() or None,
                "vehicle_model":  str(row.get("vehicle_model") or "").strip() or None,
                "policy_type":    vehicle_type,
                "expiry_date":    _parse_expiry(row.get("policy_expiry")),
            })
 
    else:
        return Response({"error": f"Unsupported file type: {ext}. Please upload .xlsx"}, status=400)
 
    batch = UploadBatch.objects.create(name=file.name, customer_count=len(customers_data))
 
    for c in customers_data:
        customer, created = Customer.objects.get_or_create(
            phone=c["phone"],
            source="outbound",          # ← separate from inbound
            defaults={
                "name":           c["name"],
                "customer_type":  c["customer_type"],
                "vehicle_type":   c["vehicle_type"],
                "vehicle_number": c["vehicle_number"],
                "vehicle_model":  c["vehicle_model"],
                "policy_type":    c["policy_type"],
                "expiry_date":    c["expiry_date"],
            },
        )
        if not created:
            customer.name           = c["name"]
            customer.customer_type  = c["customer_type"]
            customer.vehicle_type   = c["vehicle_type"]
            customer.vehicle_number = c["vehicle_number"]
            customer.vehicle_model  = c["vehicle_model"]
            customer.policy_type    = c["policy_type"]
            customer.expiry_date    = c["expiry_date"]
 
        customer.conversation_state = "initial"   # outbound customers → initial
        customer.reminder_sent      = False
        customer.batch              = batch
        customer.save()
 
    from bot.services.renewal_service import (
        RENEWAL_TEMPLATE, NEW_INSURANCE_TEMPLATE, EXPIRED_TEMPLATE, _send_and_log
    )
 
    renewal_customers = list(Customer.objects.filter(batch=batch, customer_type="renewal"))
    new_customers     = list(Customer.objects.filter(batch=batch, customer_type="new"))
 
    total      = len(renewal_customers) + len(new_customers)
    sent_count = 0
    _set_progress(sent=0, total=total, active=True)
 
    today = date.today()

    for c in renewal_customers:
        if c.expiry_date and c.expiry_date < today:
            # Policy already expired — send urgent expired message
            msg = EXPIRED_TEMPLATE.format(
                name=c.name,
                vehicle_type=c.vehicle_type,
                vehicle_number=c.vehicle_number or "N/A",
                expiry_date=c.expiry_date.strftime("%d-%m-%Y"),
            )
            print(f"[upload] EXPIRED → {c.phone} (expired {c.expiry_date})")
        else:
            # Policy expiring soon — send normal renewal reminder
            msg = RENEWAL_TEMPLATE.format(
                name=c.name,
                vehicle_type=c.vehicle_type,
                vehicle_number=c.vehicle_number or "N/A",
                expiry_date=c.expiry_date,
            )
            print(f"[upload] Renewal → {c.phone}")

        _send_and_log(c, msg)
        sent_count += 1
        _set_progress(sent=sent_count, total=total, active=True)
        time.sleep(2)
 
    for c in new_customers:
        msg = NEW_INSURANCE_TEMPLATE.format(
            name=c.name,
            vehicle_type=c.vehicle_type,
            vehicle_number=c.vehicle_number or "N/A",
        )
        print(f"[upload] New insurance → {c.phone}")
        _send_and_log(c, msg)
        sent_count += 1
        _set_progress(sent=sent_count, total=total, active=True)
        time.sleep(2)
 
    _set_progress(sent=total, total=total, active=False)
 
    return Response({
        "status":             "file processed & messages sent",
        "customers_found":    len(customers_data),
        "renewal_sent":       len(renewal_customers),
        "new_insurance_sent": len(new_customers),
    })
 
 
# ============================================================
#  UPLOAD PROGRESS
# ============================================================
 
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_upload_progress(request):
    progress = cache.get(UPLOAD_PROGRESS_KEY, {"sent": 0, "total": 0, "active": False})
    return Response(progress)
 
 
# ============================================================
#  CONVERSATION ENDPOINTS
# ============================================================
 
@api_view(["GET"])
def get_conversations(request):
    # Only return inbound (walk-in) customers
    customers = Customer.objects.filter(source="inbound").prefetch_related("chatmessage_set")
    data = []
    for c in customers:
        msgs = c.chatmessage_set.order_by("-timestamp")
        data.append({
            "id":                 c.id,
            "name":               c.name,
            "phone":              c.phone,
            "customer_type":      c.customer_type,
            "vehicle_type":       c.vehicle_type,
            "vehicle_number":     c.vehicle_number,
            "vehicle_model":      c.vehicle_model,
            "conversation_state": c.conversation_state,
            "source":             c.source,
            "batch_id":           c.batch_id,
            "last_message":       msgs.first().message if msgs.exists() else "",
        })
    return Response({"conversations": data})
 
 
@api_view(["GET"])
def get_messages(request, customer_id):
    messages = (
        ChatMessage.objects
        .filter(customer_id=customer_id)
        .order_by("timestamp")
        .values("message", "sender", "timestamp")
    )
    return Response({"messages": list(messages)})
 
 
@api_view(["POST"])
def send_message_dashboard(request):
    customer_id = request.data.get("customer_id")
    message     = request.data.get("message", "").strip()
 
    if not customer_id or not message:
        return Response({"error": "customer_id and message are required"}, status=400)
 
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)
 
    send_whatsapp_message(customer.phone, message)
    _save_msg(customer, message, "bot")
    return Response({"status": "sent"})
 
 
# ============================================================
#  DASHBOARD
# ============================================================
 
@api_view(["GET"])
def dashboard_data(request):
    customers = Customer.objects.prefetch_related("chatmessage_set").all()
 
    outbound_count = customers.filter(source="outbound").count()
    inbound_count  = customers.filter(source="inbound").count()
 
    return Response({
        "total_customers":     customers.count(),
        "total_outbound":      outbound_count,
        "total_inbound":       inbound_count,
        "total_messages":      ChatMessage.objects.count(),
        "total_conversations": customers.count(),
    })
 
 
# ============================================================
#  BATCH ENDPOINTS
# ============================================================
 
@api_view(["GET"])
def get_batches(request):
    batches = UploadBatch.objects.order_by("-uploaded_at").values(
        "id", "name", "uploaded_at", "customer_count"
    )
    return Response({"batches": list(batches)})
 
 
@api_view(["GET"])
def get_batch_customers(request, batch_id):
    customers = Customer.objects.filter(batch_id=batch_id).prefetch_related("chatmessage_set")
    data = []
    for c in customers:
        msgs = c.chatmessage_set.order_by("-timestamp")
        data.append({
            "id":             c.id,
            "name":           c.name,
            "phone":          c.phone,
            "customer_type":  c.customer_type,
            "vehicle_type":   c.vehicle_type,
            "vehicle_number": c.vehicle_number,
            "vehicle_model":  c.vehicle_model,
            "last_message":   msgs.first().message if msgs.exists() else "",
        })
    return Response({"customers": data})
 
 
# ============================================================
#  TEMPLATE VIEWS
# ============================================================
 
def dashboard_view(request):
    return render(request, "dashboard.html")
 
 
def upload_page_view(request):
    return render(request, "upload.html")

def upload_call_page(request):
    return render(request, "upload_call.html")

# @api_view(["POST"])
# def trigger_call(request):
#     try:
#         phone = request.data.get("phone")

#         if not phone:
#             return Response({"error": "Phone required"}, status=400)

#                 # ── Normalize number — provider expects without 91 prefix ──
                
#         normalized_phone = phone
#         if str(phone).startswith("91") and len(str(phone)) == 12:
#             normalized_phone = str(phone)[2:]  # strip 91 → 9104142402

#         print(f"📞 Triggering call for: {phone} → normalized: {normalized_phone}")

#         payload = {
#             "to": normalized_phone,
#             "caller_id": "+919484959435",
#             "ref": f"crm-{uuid.uuid4()}",
#             "bot_url": "wss://insurancebot-b3aha4cmfnbghza7.centralindia-01.azurewebsites.net/ws/voice-bot/?agent_id=3db2a820-2745-47b9-aa8b-f42c99f727e4"
#         }

#         response = requests.post(
#             "https://voice-bot.on-forge.com/api/dial",
#             json=payload,
#             headers={
#                 "Content-Type": "application/json",
#                 "x-api-key": "ac7c16c5a55834b5902155d32f8fef9c",
#             }
#         )

#         print("Provider response:", response.text)

#         return Response({
#             "status": "call triggered",
#             "provider_response": response.text
#         })

#     except Exception as e:
#         return Response({"error": str(e)}, status=500)





# @api_view(["POST"])
# def trigger_call(request):
#     try:
#         phones = request.data.get("phones", [])   # ✅ list instead of single

#         if not phones or not isinstance(phones, list):
#             return Response({"error": "phones list required"}, status=400)

#         results = []

#         for phone in phones:
#             # ── Normalize number ──
#             normalized_phone = phone
#             if str(phone).startswith("91") and len(str(phone)) == 12:
#                 normalized_phone = str(phone)[2:]

#             print(f"📞 Triggering call for: {phone} → {normalized_phone}")

#             payload = {
#                 "to": normalized_phone,
#                 "caller_id": "+919484959435",
#                 "ref": f"crm-{uuid.uuid4()}",
#                 "bot_url": "wss://insurancebot-b3aha4cmfnbghza7.centralindia-01.azurewebsites.net/ws/voice-bot/?agent_id=3db2a820-2745-47b9-aa8b-f42c99f727e4"
#             }

#             response = requests.post(
#                 "https://voice-bot.on-forge.com/api/dial",
#                 json=payload,
#                 headers={
#                     "Content-Type": "application/json",
#                     "x-api-key": "ac7c16c5a55834b5902155d32f8fef9c",
#                 }
#             )

#             results.append({
#                 "phone": phone,
#                 "response": response.text
#             })

#         return Response({
#             "status": "bulk call triggered",
#             "total": len(phones),
#             "results": results
#         })

#     except Exception as e:
#         return Response({"error": str(e)}, status=500)






def is_within_calling_hours():
    import sys
    if 'test' in sys.argv:
        return True

    import datetime as dt_module
    from django.utils import timezone
    utc_now = timezone.now()
    ist_tz = dt_module.timezone(dt_module.timedelta(hours=5, minutes=30))
    ist_now = utc_now.astimezone(ist_tz)
    
    start_time = dt_module.time(9, 0)
    end_time = dt_module.time(18, 0)
    
    current_time = ist_now.time()
    return start_time <= current_time <= end_time


def has_remaining_minutes(agent_id):
    from agents.models import VoiceAgent
    from conversations.models import Conversation
    import math

    from django.core.exceptions import ValidationError
    try:
        agent = VoiceAgent.objects.get(id=agent_id)
    except (VoiceAgent.DoesNotExist, ValueError, TypeError, ValidationError):
        return True # fallback if invalid agent_id

    completed = Conversation.objects.filter(
        agent=agent,
        ended_at__isnull=False
    )
    total_billed = 0.0
    for c in completed:
        raw_seconds = (c.ended_at - c.started_at).total_seconds()
        if raw_seconds > 0:
            shifted_seconds = raw_seconds + 1
            rounded_intervals = math.ceil(shifted_seconds / 30)
            total_billed += rounded_intervals * 30 / 60.0

    remaining = agent.minutes_quota - total_billed
    return remaining > 0



@api_view(["POST"])
def trigger_call(request):
    if not is_within_calling_hours():
        return Response({
            "error": "Call operations are restricted to standard operating hours (09:30 AM to 06:30 PM IST). Please initiate call requests during the next scheduled window."
        }, status=400)

    try:
        phone = request.data.get("phone")
        phones = request.data.get("phones")
        language = request.data.get("language", "en")
        
        # Resolve scoped agent if logged in
        agent_id = None
        if request.user and request.user.is_authenticated:
            is_superadmin = request.user.is_superuser
            if not is_superadmin and hasattr(request.user, "profile"):
                profile = request.user.profile
                is_admin_role = False
                if profile.role:
                    is_admin_role = profile.role.permissions.get("is_admin", False) or profile.role.name.lower() in ["super admin", "superadmin"]
                if profile.custom_permissions:
                    is_admin_role = is_admin_role or profile.custom_permissions.get("is_admin", False)
                if is_admin_role and not profile.assigned_agent:
                    is_superadmin = True
            
            if not is_superadmin and hasattr(request.user, "profile") and request.user.profile.assigned_agent:
                agent_id = str(request.user.profile.assigned_agent.id)
        
        if not agent_id:
            agent_id = request.data.get("agent_id")
        
        if not agent_id:
            return Response({"error": "No agent assigned. Please contact your admin to assign a bot to your account."}, status=400)

        # Resolve DID number from agent_id
        from agents.models import VoiceAgent
        try:
            agent = VoiceAgent.objects.get(id=agent_id)
            did_number = agent.inbound_phone_number
            if did_number:
                did_number = str(did_number).strip()
                if not did_number.startswith("+"):
                    if len(did_number) == 10:
                        did_number = "+91" + did_number
                    elif len(did_number) == 12 and did_number.startswith("91"):
                        did_number = "+" + did_number
                    else:
                        did_number = "+91" + did_number
            else:
                did_number = CALLER_ID
        except (VoiceAgent.DoesNotExist, ValueError):
            did_number = CALLER_ID

        if not has_remaining_minutes(agent_id):
            return Response({
                "error": "All allocated call credits have been utilized. Please purchase more minutes to resume calling operations."
            }, status=400)

        # ─────────────────────────────────────────────
        # CASE 1: SINGLE CALL
        # ─────────────────────────────────────────────
        if phone:
            normalized_phone = phone
            if str(phone).startswith("91") and len(str(phone)) == 12:
                normalized_phone = str(phone)[2:]

            name = request.data.get("name") or "Customer"
            name = str(name).strip()
            if not name or name.lower() == "nan":
                name = "Customer"
 
            from bot.models import Customer
            Customer.objects.update_or_create(
                phone=normalized_phone,
                defaults={"name": name, "source": "outbound"}
            )
 
            # Trigger background pre-synthesis of greeting!
            import threading
            threading.Thread(
                target=pre_synthesize_greeting,
                args=(agent_id, normalized_phone, name, language),
                daemon=True
            ).start()
 
            print(f"📞 Single Call → {normalized_phone} (Name: {name}, Lang: {language}, Agent: {agent_id})")
 

            websocket_url, webhook_url = _get_voicelink_urls(normalized_phone, agent_id, language)
            payload = {
                "leads": [
                    {
                        "customer_number": normalized_phone,
                        "custom_parameters": json.dumps({"name": name})
                    }
                ],
                "did_number": did_number,
                "webhook_url": webhook_url,
                "country_code": "91",
                "websocket_url": websocket_url
            }


            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {TELECOM_API_KEY}",
                "x-api-key": TELECOM_API_KEY,
            }
            try:
                response = requests.post(
                    "https://app.voicelink.co.in/api/v1/add_lead",
                    json=payload,
                    headers=headers,
                    timeout=15
                )
                if response.status_code not in [200, 201]:
                    return Response({
                        "error": f"Voicelink telephony error ({response.status_code}): {response.text}"
                    }, status=400)
            except Exception as e:
                return Response({
                    "error": f"Failed to connect to Voicelink telephony service: {str(e)}"
                }, status=500)

            return Response({
                "type": "single",
                "response": response.text
            })

        # ─────────────────────────────────────────────
        # CASE 2: BULK CALL
        # ─────────────────────────────────────────────
        elif phones and isinstance(phones, list):

            results = []

            for phone in phones:
                normalized_phone = phone
                if str(phone).startswith("91") and len(str(phone)) == 12:
                    normalized_phone = str(phone)[2:]

                print(f"📞 Bulk Call → {normalized_phone} (Lang: {language}, Agent: {agent_id})")

                websocket_url, webhook_url = _get_voicelink_urls(normalized_phone, agent_id, language)
                payload = {
                    "leads": [
                        {
                            "customer_number": normalized_phone,
                            "custom_parameters": json.dumps({"name": "Valued Customer"})
                        }
                    ],
                    "did_number": did_number,
                    "webhook_url": webhook_url,
                    "country_code": "91",
                    "websocket_url": websocket_url
                }

                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {TELECOM_API_KEY}",
                    "x-api-key": TELECOM_API_KEY,
                }
                try:
                    response = requests.post(
                        "https://app.voicelink.co.in/api/v1/add_lead",
                        json=payload,
                        headers=headers,
                        timeout=15
                    )
                    if response.status_code not in [200, 201]:
                        results.append({
                            "phone": phone,
                            "error": f"Voicelink error ({response.status_code}): {response.text}"
                        })
                        continue
                except Exception as e:
                    results.append({
                        "phone": phone,
                        "error": f"Connection error: {str(e)}"
                    })
                    continue

                results.append({
                    "phone": phone,
                    "response": response.text
                })

            return Response({
                "type": "bulk",
                "total": len(phones),
                "results": results
            })

        # ─────────────────────────────────────────────
        # ERROR CASE
        # ─────────────────────────────────────────────
        else:
            return Response({
                "error": "Provide either 'phone' or 'phones'"
            }, status=400)

    except Exception as e:
        return Response({"error": str(e)}, status=500)



@api_view(["POST"])
def upload_call_file(request):
    # Temporarily bypassed for testing
    # if not is_within_calling_hours():
    #     return Response({
    #         "error": "Campaign call operations are restricted to standard operating hours (09:30 AM to 06:30 PM IST). Please upload and trigger call campaigns during the next scheduled window."
    #     }, status=400)

    """
    Upload an Excel file with phone numbers.
    Uses the AUTO-DIALER queue — only 2 calls at a time.
    When one call ends, the next is auto-triggered.
    """
    global _campaign_active, _campaign_stats, _campaign_paused, BOT_URL

    file = request.FILES.get("file")
    
    # Resolve scoped agent if logged in
    agent_id = None
    if request.user and request.user.is_authenticated:
        is_superadmin = request.user.is_superuser
        if not is_superadmin and hasattr(request.user, "profile"):
            profile = request.user.profile
            is_admin_role = False
            if profile.role:
                is_admin_role = profile.role.permissions.get("is_admin", False) or profile.role.name.lower() in ["super admin", "superadmin"]
            if profile.custom_permissions:
                is_admin_role = is_admin_role or profile.custom_permissions.get("is_admin", False)
            if is_admin_role and not profile.assigned_agent:
                is_superadmin = True
                
        if not is_superadmin and hasattr(request.user, "profile") and request.user.profile.assigned_agent:
            agent_id = str(request.user.profile.assigned_agent.id)
            
    if not agent_id:
        agent_id = request.data.get("agent_id") or request.POST.get("agent_id")
    
    if not agent_id:
        return Response({"error": "No agent assigned. Please contact your admin to assign a bot to your account."}, status=400)

    if not has_remaining_minutes(agent_id):
        return Response({
            "error": "All allocated call credits have been utilized. Please purchase more minutes to resume calling operations."
        }, status=400)

    BOT_URL = f"wss://unprecious-waltraud-nasological.ngrok-free.dev/ws/voice-bot/service2/?agent_id={agent_id}"

    if not file:
        return Response({"error": "No file uploaded"}, status=400)

    if _campaign_active:
        with _call_queue_lock:
            remaining = len(_call_queue)
            active = len(_active_calls)
        return Response({
            "error": "A campaign is already running. Stop it first.",
            "active_calls": active,
            "remaining_in_queue": remaining,
        }, status=409)

    try:
        df = pd.read_excel(file)
    except Exception as e:
        return Response({"error": f"Failed to read Excel file: {e}"}, status=400)

    # Find the phone column case-insensitively
    phone_col = None
    for col in df.columns:
        c_clean = str(col).strip().lower()
        if c_clean in ["phone", "phone number", "mobile", "mobile number", "number", "phone_number", "contact"]:
            phone_col = col
            break
            
    if not phone_col and len(df.columns) > 0:
        phone_col = df.columns[0]

    # Find the name column case-insensitively
    name_col = None
    for col in df.columns:
        c_clean = str(col).strip().lower()
        if c_clean in ["name", "customer name", "customer_name", "first name", "first_name"]:
            name_col = col
            break
 
    from bot.models import Customer
    phones = []
    if phone_col is not None:
        for _, row in df.iterrows():
            phone = str(row.get(phone_col) or "").strip()
            if not phone:
                continue
            normalized = _normalize_phone(phone)
            if normalized:
                phones.append(normalized)
                cust_name = str(row.get(name_col) or "Customer").strip() if name_col else "Customer"
                if not cust_name or cust_name.lower() == "nan":
                    cust_name = "Customer"
                Customer.objects.update_or_create(
                    phone=normalized,
                    defaults={"name": cust_name, "source": "outbound"}
                )

    phones = [p for p in phones if p]

    if not phones:
        return Response({"error": "No valid phone numbers found in file"}, status=400)

    # Load queue and start auto-dialer
    with _call_queue_lock:
        _call_queue.clear()
        _active_calls.clear()
        _answered_calls.clear()
        _call_queue.extend(phones)

    _campaign_active = True
    _campaign_paused = False
    _campaign_stats["total"] = len(phones)
    _campaign_stats["completed"] = 0
    _campaign_stats["started_at"] = timezone.now().isoformat()
    _missed_calls.clear()
    _save_campaign_state()

    # Create a Campaign history record
    # campaign_name = file.name
    campaign_name = request.POST.get("campaign_name", "").strip() or file.name
    try:
        campaign_obj = Campaign.objects.create(
            name=campaign_name or f"Campaign {timezone.now().strftime('%d %b %Y %I:%M %p')}",
            phone_list=json.dumps(phones),
            total_count=len(phones),
            is_active=True,
            created_by=request.user if request.user and request.user.is_authenticated else None,
            agent_id=agent_id,
        )
        global _current_campaign_id
        _current_campaign_id = campaign_obj.id
        from agents.models import VoiceAgent
        agent_obj = VoiceAgent.objects.filter(id=agent_id).first()
        concurrency_limit = agent_obj.max_concurrent_calls if agent_obj else 2
        print(f"🚀 AUTO-DIALER (file upload): Campaign #{campaign_obj.id} started with {len(phones)} numbers (max {concurrency_limit} concurrent)")
    except Exception as e:
        _current_campaign_id = None
        concurrency_limit = 2
        print(f"WARNING: Failed to create Campaign record: {e}")

    # Dial first numbers
    dial_next_from_queue()

    return Response({
        "status": "campaign_started",
        "total": len(phones),
        "concurrent_calls": concurrency_limit,
        "campaign_id": _current_campaign_id,
        "message": f"First {min(concurrency_limit, len(phones))} calls triggered. Remaining will auto-dial as each call ends.",
    })


# =========================================================
# 🔄 AUTO-DIALER — 2 Concurrent Calls
# =========================================================
# Maintains 2 active calls at all times. When one call ends
# (CDR webhook fires), the next number is dialed to fill the slot.

import threading

# Thread-safe call queue
_call_queue_lock = threading.Lock()
_call_queue = []              # Phone numbers waiting to be dialed
_active_calls = set()         # Phone numbers currently being called
_answered_calls = set()       # Phone numbers that picked up
_campaign_active = False
_campaign_paused = False
_campaign_suspended_hours = False
MAX_CONCURRENT_CALLS = 2      # Always keep 2 calls active
_current_campaign_id = None   # ID of the active Campaign record

_campaign_stats = {
    "total": 0,
    "completed": 0,
    "started_at": None,
}
_missed_calls = []            # Numbers that timed out (No Answer)

# Telecom config
TELECOM_DIAL_URL = "https://app.voicelink.co.in/api/v1/add_lead"
TELECOM_API_KEY = "729230|7gNpRt1e7KzmxvRkmG5bG9IwJhEQJFXkUri3XtaNfe6bc240"
CALLER_ID = "+919484959435"
BOT_URL = "wss://unprecious-waltraud-nasological.ngrok-free.dev/ws/voice-bot/service2/?agent_id={agent_id}"


def _normalize_phone(phone):
    """Normalize phone number — strip +91 prefix if present."""
    phone_str = str(phone).strip()
    if phone_str.endswith(".0"):
        phone_str = phone_str[:-2]
    if "/" in phone_str:
        phone_str = phone_str.split("/")[0].strip()
    if phone_str.startswith("+91") and len(phone_str) == 13:
        phone_str = phone_str[3:]
    elif phone_str.startswith("91") and len(phone_str) == 12:
        phone_str = phone_str[2:]
    return phone_str


def _get_voicelink_urls(phone, agent_id, language="hi", campaign_id=None):
    """Derive WebSocket and Webhook URLs from the configured BOT_URL."""
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(BOT_URL)
        domain = parsed.netloc
        ws_scheme = parsed.scheme or "wss"
    except Exception:
        domain = "unprecious-waltraud-nasological.ngrok-free.dev"
        ws_scheme = "wss"
        
    websocket_url = f"{ws_scheme}://{domain}/ws/voice-bot/service2/?agent_id={agent_id}&language={language}&phone={phone}"
    if campaign_id:
        websocket_url += f"&campaign_id={campaign_id}"
        
    http_scheme = "https" if ws_scheme == "wss" else "http"
    webhook_url = f"{http_scheme}://{domain}/api/webhook/cdr/"
    
    return websocket_url, webhook_url


# ── Campaign State Management ────────────────────────
def _save_campaign_state():
    """Helper to persist in-memory campaign state to DB."""
    try:
        # Use a singleton pattern (one record for the last campaign)
        status, created = CampaignStatus.objects.get_or_create(id=1)
        status.total_count = _campaign_stats.get("total", 0)
        status.completed_count = _campaign_stats.get("completed", 0)
        status.missed_calls = json.dumps(_missed_calls)
        status.answered_calls = json.dumps(list(_answered_calls))
        status.is_active = _campaign_active
        if not status.started_at:
             status.started_at = timezone.now()
        global _campaign_suspended_hours, _call_queue
        status.suspended_due_to_hours = _campaign_suspended_hours
        status.remaining_queue = json.dumps(_call_queue)
        status.save()
        
        # Also sync to Campaign history record if active
        if _current_campaign_id:
            try:
                campaign = Campaign.objects.get(id=_current_campaign_id)
                campaign.completed_count = _campaign_stats.get("completed", 0)
                campaign.answered_count = max(0, campaign.completed_count - len(_missed_calls))
                campaign.missed_calls = json.dumps(_missed_calls)
                campaign.answered_calls = json.dumps(list(_answered_calls))
                campaign.remaining_queue = json.dumps(_call_queue)
                campaign.save()
            except Exception as ex:
                print(f"WARNING: Failed to sync campaign history record during save state: {ex}")
    except Exception as e:
        print(f"❌ ERROR: Failed to save campaign state: {e}")

def _load_campaign_state():
    """Load the last campaign state from DB into memory."""
    global _campaign_active, _campaign_stats, _missed_calls, _answered_calls, _campaign_suspended_hours, _call_queue
    try:
        status = CampaignStatus.objects.get(id=1)
        _campaign_stats["total"] = status.total_count
        _campaign_stats["completed"] = status.completed_count
        _missed_calls = json.loads(status.missed_calls) if status.missed_calls else []
        _answered_calls = set(json.loads(status.answered_calls)) if hasattr(status, 'answered_calls') and status.answered_calls else set()
        _campaign_suspended_hours = status.suspended_due_to_hours
        if status.is_active or status.suspended_due_to_hours:
            _call_queue = json.loads(status.remaining_queue) if status.remaining_queue else []
    except CampaignStatus.DoesNotExist:
        pass
    except Exception as e:
        print(f"❌ ERROR: Failed to load campaign state: {e}")


def auto_resume_suspended_campaigns():
    """
    Background worker loop that checks for campaigns suspended due to calling hours
    and resumes them when calling hours reset (after 09:30 AM).
    """
    import time
    import traceback
    print("⏳ Starting background calling hours scheduler...")
    while True:
        try:
            # Check every 60 seconds
            time.sleep(60)
            
            is_open = is_within_calling_hours()
            
            # If calling hours are open and we have a suspended campaign
            if is_open:
                from bot.models import CampaignStatus, Campaign
                # Look for a suspended campaign in the Campaign history records
                camp = Campaign.objects.filter(is_active=True, suspended_due_to_hours=True).order_by("-started_at").first()
                if camp:
                    print(f"⏰ Calling hours are open! Resuming suspended campaign #{camp.id}...")
                    global _campaign_active, _campaign_paused, _campaign_suspended_hours, _current_campaign_id, _call_queue, _answered_calls
                    
                    status, _ = CampaignStatus.objects.get_or_create(id=1)
                    with _call_queue_lock:
                        _campaign_active = True
                        _campaign_paused = False
                        _campaign_suspended_hours = False
                        _current_campaign_id = camp.id
                        _call_queue = json.loads(camp.remaining_queue) if camp.remaining_queue else []
                        _answered_calls = set(json.loads(camp.answered_calls)) if hasattr(camp, 'answered_calls') and camp.answered_calls else set()
                        
                        camp.suspended_due_to_hours = False
                        camp.remaining_queue = "[]"
                        camp.save()
                        
                        status.suspended_due_to_hours = False
                        status.remaining_queue = "[]"
                        status.answered_calls = camp.answered_calls
                        status.is_active = True
                        status.save()
                        
                        print(f"🔥 Resuming campaign #{camp.id} with {len(_call_queue)} remaining calls.")
                    
                    dial_next_from_queue()
        except Exception as e:
            print(f"❌ Error in background calling hours scheduler: {e}")
            traceback.print_exc()

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def mark_answered(request):
    """API for the bot to signal that a call was answered."""
    phone = request.data.get("phone")
    if phone:
        clean_phone = _normalize_phone(phone)
        with _call_queue_lock:
            _answered_calls.add(clean_phone)
        return Response({"status": "marked_answered"})
    return Response({"error": "No phone"}, status=400)


def on_call_completed(phone, success=True):
    """Callback from bot logic when a call actually finishes (hangup)."""
    with _call_queue_lock:
        _campaign_stats["completed"] += 1
        _active_calls.discard(phone)
        _save_campaign_state() # Persist

    # Dial the next one in line
    dial_next_from_queue()


def dial_next_from_queue():
    """
    Fills empty call slots from the queue.
    Called after CDR webhook fires (a call ended) or at campaign start.
    Returns the number of new calls triggered.
    """
    global _campaign_active, _campaign_paused, _campaign_suspended_hours, _current_campaign_id

    if not is_within_calling_hours():
        print("AUTO-DIALER: Daily calling window has closed. Pausing campaign and rescheduling remaining calls.")
        with _call_queue_lock:
            _campaign_suspended_hours = True
            _campaign_paused = True
            
            if _current_campaign_id:
                try:
                    camp = Campaign.objects.get(id=_current_campaign_id)
                    camp.suspended_due_to_hours = True
                    camp.remaining_queue = json.dumps(_call_queue)
                    camp.save()
                except Campaign.DoesNotExist:
                    pass
            
            _save_campaign_state()
        return 0

    if _campaign_paused:
        print("AUTO-DIALER: Dialer is paused. Skipping dialing next.")
        return 0

    calls_triggered = 0

    while True:
        import re
        agent_id_match = re.search(r'agent_id=([^&]+)', BOT_URL)
        if agent_id_match:
            current_agent_id = agent_id_match.group(1)
            if not has_remaining_minutes(current_agent_id):
                with _call_queue_lock:
                    _campaign_active = False
                    _save_campaign_state()
                    _finalize_campaign()
                print("AUTO-DIALER: Campaign stopped because all minutes quota is exhausted.")
                break

        # Fetch dynamic concurrency limit for this campaign's agent
        concurrency_limit = 2
        if _current_campaign_id:
            try:
                from bot.models import Campaign
                camp = Campaign.objects.select_related('agent').get(id=_current_campaign_id)
                if camp.agent:
                    concurrency_limit = camp.agent.max_concurrent_calls
            except Exception as e:
                print(f"Error fetching campaign concurrency limit: {e}")

        with _call_queue_lock:
            # Check if we have room for more calls
            if len(_active_calls) >= concurrency_limit:
                break

            # Check if queue has numbers left
            if not _call_queue:
                # Queue empty — if no active calls either, campaign is done
                if not _active_calls:
                    _campaign_active = False
                    _save_campaign_state() # Persist the finished state!
                    _finalize_campaign()   # Close the Campaign history record
                    print("AUTO-DIALER: Campaign complete - all calls finished.")
                break

            phone = _call_queue.pop(0)
            normalized = _normalize_phone(phone)
            _active_calls.add(normalized)

        # Dial outside the lock
        agent_id = "default"
        if _current_campaign_id:
            try:
                curr_camp = Campaign.objects.get(id=_current_campaign_id)
                agent_id = curr_camp.agent_id
            except Campaign.DoesNotExist:
                pass
        if agent_id == "default" or agent_id == "{agent_id}":
            import re
            agent_id_match = re.search(r'agent_id=([^&]+)', BOT_URL)
            if agent_id_match:
                parsed_agent = agent_id_match.group(1)
                if parsed_agent != "{agent_id}":
                    agent_id = parsed_agent

        websocket_url, webhook_url = _get_voicelink_urls(normalized, agent_id, campaign_id=_current_campaign_id)

        # Retrieve customer name from database Customer model
        from bot.models import Customer
        clean_phone = "".join(filter(str.isdigit, str(normalized)))[-10:]
        cust = Customer.objects.filter(phone__endswith=clean_phone).first()
        cust_name = cust.name if (cust and cust.name and cust.name.lower() != "user") else "Customer"
 
        # Trigger background pre-synthesis of greeting!
        import threading
        threading.Thread(
            target=pre_synthesize_greeting,
            args=(agent_id, normalized, cust_name, "hi"),  # Default to Hindi for Aaisha bot
            daemon=True
        ).start()

        # Resolve DID number from agent_id
        from agents.models import VoiceAgent
        try:
            agent = VoiceAgent.objects.get(id=agent_id)
            did_number = agent.inbound_phone_number
            if did_number:
                did_number = str(did_number).strip()
                if not did_number.startswith("+"):
                    if len(did_number) == 10:
                        did_number = "+91" + did_number
                    elif len(did_number) == 12 and did_number.startswith("91"):
                        did_number = "+" + did_number
                    else:
                        did_number = "+91" + did_number
            else:
                did_number = CALLER_ID
        except (VoiceAgent.DoesNotExist, ValueError):
            did_number = CALLER_ID

        payload = {
            "leads": [
                {
                    "customer_number": normalized,
                    "custom_parameters": json.dumps({"name": cust_name})
                }
            ],
            "did_number": did_number,
            "webhook_url": webhook_url,
            "country_code": "91",
            "websocket_url": websocket_url
        }

        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {TELECOM_API_KEY}",
                "x-api-key": TELECOM_API_KEY,
            }
            resp = requests.post(
                TELECOM_DIAL_URL,
                json=payload,
                headers=headers,
                timeout=15,
            )
            print(f"📞 AUTO-DIALER: Calling {normalized} → Status {resp.status_code} | Active: {len(_active_calls)} | Queue: {len(_call_queue)}")
            
            if resp.status_code not in [200, 201]:
                print(f"❌ AUTO-DIALER: Failed to dial {normalized} (Status {resp.status_code}): {resp.text}")
                with _call_queue_lock:
                    _active_calls.discard(normalized)
                _campaign_stats["completed"] += 1
                # Trigger next call immediately since this one failed
                import threading
                threading.Timer(1.0, dial_next_from_queue).start()
                continue

            # ⏱ WATCHDOG: If call isn't picked up in 60s, force-end it to trigger next
            import threading
            threading.Timer(35.0, on_call_timeout, args=[normalized]).start()
            
            calls_triggered += 1
        except Exception as e:
            print(f"❌ AUTO-DIALER: Failed to dial {normalized} — {e}")
            with _call_queue_lock:
                _active_calls.discard(normalized)
            _campaign_stats["completed"] += 1
            # Try next number
            import threading
            threading.Timer(1.0, dial_next_from_queue).start()

    return calls_triggered


def on_call_ended(phone_number):
    """
    Called when a call ends (either via CDR webhook or WebSocket disconnect).
    Removes the phone from active calls and triggers the next dial.
    """
    if not phone_number:
        return

    clean_phone = "".join(filter(str.isdigit, str(phone_number)))[-10:]

    found = False
    with _call_queue_lock:
        # Remove from active calls (match by last 10 digits)
        to_remove = None
        for active in _active_calls:
            active_clean = "".join(filter(str.isdigit, active))[-10:]
            if active_clean == clean_phone:
                to_remove = active
                break
        
        if to_remove:
            # If the call was never answered, it is a missed call.
            # We check both the in-memory _answered_calls set and the database Conversations.
            was_answered = False
            for ans in _answered_calls:
                ans_clean = "".join(filter(str.isdigit, str(ans)))[-10:]
                if ans_clean == clean_phone:
                    was_answered = True
                    break
                   
            if not was_answered:
                try:
                    from conversations.models import Conversation
                    import datetime
                    from django.utils import timezone
                   
                    filters = {
                        "user_number__icontains": clean_phone,
                    }
                    if _current_campaign_id:
                        filters["campaign_id"] = _current_campaign_id
                    else:
                        filters["started_at__gte"] = timezone.now() - datetime.timedelta(minutes=30)
                       
                    was_answered = Conversation.objects.filter(**filters).exists()
                except Exception as e:
                    print(f"⚠️ Error checking conversation in DB: {e}")
                   
            if not was_answered:
                if to_remove not in _missed_calls:
                    _missed_calls.append(to_remove)
                   
            _active_calls.discard(to_remove)
            _answered_calls.discard(to_remove) # Cleanup
            _campaign_stats["completed"] += 1
            found = True
 

    if not found:
        # Already handled or not part of this campaign
        return

    print(f"🔄 AUTO-DIALER: Call ended ({clean_phone}) | Active: {len(_active_calls)} | Queue: {len(_call_queue)}")

    # Save campaign state
    _save_campaign_state()

    # Fill the empty slot
    if _campaign_active:
        import threading
        threading.Timer(2.0, dial_next_from_queue).start()


def on_call_timeout(phone_number):
    """
    Called after 35s if the call hasn't ended naturally.
    If it's still in _active_calls AND NOT in _answered_calls, we assume 'No Answer'.
    """
    clean_phone = "".join(filter(str.isdigit, str(phone_number)))[-10:]
 
    with _call_queue_lock:
        # If the call was already answered, don't mark as missed!
        was_answered = False
        for ans in _answered_calls:
            ans_clean = "".join(filter(str.isdigit, str(ans)))[-10:]
            if ans_clean == clean_phone:
                was_answered = True
                break
               
        if not was_answered:
            try:
                from conversations.models import Conversation
                import datetime
                from django.utils import timezone
               
                filters = {
                    "user_number__icontains": clean_phone,
                }
                if _current_campaign_id:
                    filters["campaign_id"] = _current_campaign_id
                else:
                    filters["started_at__gte"] = timezone.now() - datetime.timedelta(minutes=30)
                   
                was_answered = Conversation.objects.filter(**filters).exists()
            except Exception as e:
                print(f"⚠️ Error checking conversation in DB during timeout: {e}")
 
        if was_answered:
            print(f"✅ AUTO-DIALER: Call was answered by {phone_number}, ignoring timeout.")
            return

        if phone_number in _active_calls:
            print(f"⌛ AUTO-DIALER: Call Timeout ({phone_number}) — No Answer/Busy. Moving to next...")
            if phone_number not in _missed_calls:
                _missed_calls.append(phone_number)
            _save_campaign_state() # Persist
        else:
            return

    # Call on_call_ended to clean up and trigger next
    on_call_ended(phone_number)



@api_view(["POST"])
def start_auto_campaign(request):
    # Temporarily bypassed for testing
    # if not is_within_calling_hours():
    #     return Response({
    #         "error": "Campaign call operations are restricted to standard operating hours (09:30 AM to 06:30 PM IST). Please initiate call campaigns during the next scheduled window."
    #     }, status=400)

    _ensure_state_loaded()
    """
    Start an auto-dial campaign with 2 concurrent calls.
    When each call ends (CDR webhook), the next number is dialed automatically.

    POST body:
        { "phones": ["9909466119", "9876543210", ...], "agent_id": "..." }
    OR upload an Excel file:
        form-data: file=<excel>, field name "file"
    """
    global _campaign_active, _campaign_stats, _current_campaign_id, _campaign_paused, BOT_URL

    # Resolve scoped agent if logged in
    agent_id = None
    if request.user and request.user.is_authenticated:
        if hasattr(request.user, "profile") and request.user.profile.assigned_agent:
            agent_id = str(request.user.profile.assigned_agent.id)
            
    if not agent_id:
        agent_id = request.data.get("agent_id") or request.POST.get("agent_id")
    
    if not agent_id:
        return Response({"error": "No agent assigned. Please contact your admin to assign a bot to your account."}, status=400)

    if not has_remaining_minutes(agent_id):
        return Response({
            "error": "All allocated call credits have been utilized. Please purchase more minutes to resume calling operations."
        }, status=400)

    BOT_URL = f"wss://unprecious-waltraud-nasological.ngrok-free.dev/ws/voice-bot/service2/?agent_id={agent_id}"

    if _campaign_active:
        with _call_queue_lock:
            remaining = len(_call_queue)
            active = len(_active_calls)
        return Response({
            "error": "A campaign is already running",
            "active_calls": active,
            "remaining_in_queue": remaining,
        }, status=409)

    phones = []
    campaign_name = request.data.get("name", "")

    # Option 1: JSON list of phones
    if request.data.get("phones"):
        phones = request.data["phones"]

    # Option 2: Excel file upload
    elif request.FILES.get("file"):
        file = request.FILES["file"]
        campaign_name = campaign_name or file.name
        try:
            df = pd.read_excel(file)
            phone_col = None
            for col in df.columns:
                c_clean = str(col).strip().lower()
                if c_clean in ["phone", "phone number", "mobile", "mobile number", "number", "phone_number", "contact"]:
                    phone_col = col
                    break
            if not phone_col and len(df.columns) > 0:
                phone_col = df.columns[0]
            
            # Find the name column case-insensitively
            name_col = None
            for col in df.columns:
                c_clean = str(col).strip().lower()
                if c_clean in ["name", "customer name", "customer_name", "first name", "first_name"]:
                    name_col = col
                    break
 
            from bot.models import Customer
            
            phones = []
            if phone_col is not None:
               for _, row in df.iterrows():
                    phone = str(row.get(phone_col) or "").strip()
                    if not phone:
                        continue
                    normalized = _normalize_phone(phone)
                    if normalized:
                        phones.append(normalized)
                        cust_name = str(row.get(name_col) or "Customer").strip() if name_col else "Customer"
                        if not cust_name or cust_name.lower() == "nan":
                            cust_name = "Customer"
                        Customer.objects.update_or_create(
                            phone=normalized,
                            defaults={"name": cust_name, "source": "outbound"}
                        )
        except Exception as e:
            return Response({"error": f"Failed to read Excel file: {e}"}, status=400)

    else:
        return Response({"error": "Provide 'phones' list or upload an Excel file"}, status=400)

    if not phones:
        return Response({"error": "No phone numbers provided"}, status=400)

    # Normalize all numbers
    phones = [_normalize_phone(p) for p in phones if p]
    phones = [p for p in phones if p]

    # Load the queue
    with _call_queue_lock:
        _call_queue.clear()
        _active_calls.clear()
        _answered_calls.clear() # Reset for new campaign
        _call_queue.extend(phones)

    _campaign_active = True
    _campaign_paused = False
    _campaign_stats["total"] = len(phones)
    _campaign_stats["completed"] = 0
    _campaign_stats["started_at"] = timezone.now().isoformat()

    _missed_calls.clear()
    _save_campaign_state() # Persist new campaign

    # Create a Campaign history record
    try:
        campaign_obj = Campaign.objects.create(
            name=campaign_name or f"Campaign {timezone.now().strftime('%d %b %Y %I:%M %p')}",
            phone_list=json.dumps(phones),
            total_count=len(phones),
            is_active=True,
            created_by=request.user if request.user and request.user.is_authenticated else None,
            agent_id=agent_id,
        )
        _current_campaign_id = campaign_obj.id
        from agents.models import VoiceAgent
        agent_obj = VoiceAgent.objects.filter(id=agent_id).first()
        concurrency_limit = agent_obj.max_concurrent_calls if agent_obj else 2
        print(f"AUTO-DIALER: Campaign #{campaign_obj.id} started with {len(phones)} numbers (max {concurrency_limit} concurrent)")
    except Exception as e:
        _current_campaign_id = None
        concurrency_limit = 2
        print(f"WARNING: Failed to create Campaign record: {e}")

    # Dial the first numbers
    dial_next_from_queue()

    return Response({
        "status": "campaign_started",
        "total_numbers": len(phones),
        "concurrent_calls": concurrency_limit,
        "campaign_id": _current_campaign_id,
        "message": f"First {min(concurrency_limit, len(phones))} calls triggered. Remaining calls auto-dial as each call ends.",
    })


def _is_campaign_visible_to_user(campaign, user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    
    assigned_agent = None
    if hasattr(user, "profile"):
        assigned_agent = user.profile.assigned_agent
        
    if not assigned_agent:
        return True # Superadmin (no assigned agent limits)
        
    # Scoped user: only if campaign is for their agent, and wasn't created by a superadmin
    if campaign.agent != assigned_agent:
        return False
        
    if campaign.created_by:
        if campaign.created_by.is_superuser:
            return False
        if hasattr(campaign.created_by, "profile") and campaign.created_by.profile.assigned_agent is None:
            return False
            
    return True


@api_view(["GET"])
def auto_campaign_status(request):
    _ensure_state_loaded()
    """Returns the current status of the auto-dial campaign."""
    
    if _current_campaign_id:
        try:
            curr_camp = Campaign.objects.get(id=_current_campaign_id)
            if not _is_campaign_visible_to_user(curr_camp, request.user):
                return Response({
                    "active": False,
                    "total": 0,
                    "completed": 0,
                    "remaining_in_queue": 0,
                    "active_calls": [],
                    "no_answer_count": 0,
                })
        except Campaign.DoesNotExist:
            pass
    
    # If in-memory is empty but we aren't active, try loading from DB to restore IF it's still marked active or suspended
    if not _campaign_active and _campaign_stats.get("total") == 0:
        try:
            status = CampaignStatus.objects.get(id=1)
            if not status.is_active and not status.suspended_due_to_hours:
                # If not active in DB, don't show the card
                return Response({
                    "active": False,
                    "suspended_due_to_hours": False,
                    "total": 0,
                    "completed": 0,
                    "remaining_in_queue": 0,
                    "active_calls": [],
                    "no_answer_count": 0,
                })

            # Resolve dynamic concurrency limit
            camp_limit = 2
            try:
                last_camp = Campaign.objects.filter(is_active=True).order_by("-started_at").first()
                if last_camp and last_camp.agent:
                    camp_limit = last_camp.agent.max_concurrent_calls
            except:
                pass

            return Response({
                "active": status.is_active,
                "suspended_due_to_hours": status.suspended_due_to_hours,
                "total": status.total_count,
                "completed": status.completed_count,
                "remaining_in_queue": len(json.loads(status.remaining_queue)) if status.remaining_queue else 0,
                "active_calls": [],
                "no_answer_list": json.loads(status.missed_calls),
                "no_answer_count": len(json.loads(status.missed_calls)),
                "concurrent_limit": camp_limit,
                "started_at": status.started_at.isoformat() if status.started_at else None,
            })
        except:
            pass

    # Resolve dynamic concurrency limit for current campaign
    camp_limit = 2
    if _current_campaign_id:
        try:
            from bot.models import Campaign
            camp = Campaign.objects.select_related('agent').get(id=_current_campaign_id)
            if camp.agent:
                camp_limit = camp.agent.max_concurrent_calls
        except:
            pass

    with _call_queue_lock:
        remaining = len(_call_queue)
        active = list(_active_calls)

    # If the campaign is over, we should return total: 0 so the frontend hides the card
    # (unless it's suspended due to hours)
    final_active = _campaign_active or _campaign_suspended_hours
    final_total = _campaign_stats.get("total", 0) if final_active else 0
    final_completed = _campaign_stats.get("completed", 0) if final_active else 0

    return Response({
        "active": final_active,
        "suspended_due_to_hours": _campaign_suspended_hours,
        "paused": _campaign_paused,
        "total": final_total,
        "completed": final_completed,
        "remaining_in_queue": remaining if final_active else 0,
        "active_calls": active if final_active else [],
        "no_answer_list": _missed_calls if final_active else [],
        "no_answer_count": len(_missed_calls) if final_active else 0,
        "concurrent_limit": camp_limit,
        "started_at": _campaign_stats.get("started_at") if final_active else None,
    })


@api_view(["POST"])
def stop_auto_campaign(request):
    """Stops the current auto-dial campaign."""
    global _campaign_active, _campaign_paused

    if _current_campaign_id:
        try:
            curr_camp = Campaign.objects.get(id=_current_campaign_id)
            if not _is_campaign_visible_to_user(curr_camp, request.user):
                return Response({"error": "You do not have permission to control this campaign."}, status=403)
        except Campaign.DoesNotExist:
            pass

    with _call_queue_lock:
        remaining = len(_call_queue)
        _call_queue.clear()
        _active_calls.clear()

    _campaign_active = False
    _campaign_paused = False
    _finalize_campaign() # Close the Campaign history record

    print(f"AUTO-DIALER: Campaign stopped. {remaining} numbers were still in queue.")

    return Response({
        "status": "campaign_stopped",
        "numbers_cancelled": remaining,
    })


@api_view(["POST"])
def pause_auto_campaign(request):
    """Pauses the current auto-dial campaign."""
    global _campaign_paused
    if not _campaign_active:
        return Response({"error": "No active campaign running"}, status=400)

    if _current_campaign_id:
        try:
            curr_camp = Campaign.objects.get(id=_current_campaign_id)
            if not _is_campaign_visible_to_user(curr_camp, request.user):
                return Response({"error": "You do not have permission to control this campaign."}, status=403)
        except Campaign.DoesNotExist:
            pass

    _campaign_paused = True
    print("AUTO-DIALER: Campaign paused.")
    return Response({"status": "campaign_paused"})


@api_view(["POST"])
def resume_auto_campaign(request):
    """Resumes the current auto-dial campaign."""
    global _campaign_active, _campaign_paused, _campaign_suspended_hours, _current_campaign_id, _call_queue, _answered_calls
    
    # If there is no active campaign in memory, try to restore the campaign from the DB
    if not _campaign_active:
        # Look for any campaign in the DB that is active (is_active=True)
        camp = Campaign.objects.filter(is_active=True).order_by("-started_at").first()
        if camp:
            if not _is_campaign_visible_to_user(camp, request.user):
                return Response({"error": "You do not have permission to control this campaign."}, status=403)
            with _call_queue_lock:
                _campaign_active = True
                _campaign_paused = False
                _campaign_suspended_hours = False
                _current_campaign_id = camp.id
                _call_queue = json.loads(camp.remaining_queue) if camp.remaining_queue else []
                _answered_calls = set(json.loads(camp.answered_calls)) if hasattr(camp, 'answered_calls') and camp.answered_calls else set()
                
                # Update CampaignStatus singleton too
                status, _ = CampaignStatus.objects.get_or_create(id=1)
                status.is_active = True
                status.suspended_due_to_hours = False
                status.remaining_queue = camp.remaining_queue
                status.answered_calls = camp.answered_calls
                status.save()
                
                camp.suspended_due_to_hours = False
                camp.save()
            print(f"AUTO-DIALER: Restored and resumed campaign #{camp.id} from DB with {len(_call_queue)} remaining calls.")
        else:
            return Response({"error": "No active campaign running"}, status=400)
    else:
        # Campaign is active in memory
        if _current_campaign_id:
            try:
                curr_camp = Campaign.objects.get(id=_current_campaign_id)
                if not _is_campaign_visible_to_user(curr_camp, request.user):
                    return Response({"error": "You do not have permission to control this campaign."}, status=403)
                curr_camp.suspended_due_to_hours = False
                curr_camp.save()
            except Campaign.DoesNotExist:
                pass
            
            status, _ = CampaignStatus.objects.get_or_create(id=1)
            status.suspended_due_to_hours = False
            status.is_active = True
            status.save()

        _campaign_paused = False
        _campaign_suspended_hours = False

    print("AUTO-DIALER: Campaign resumed. Dialing next...")
    dial_next_from_queue()
    return Response({"status": "campaign_resumed"})


@api_view(["GET"])
def export_leads_excel(request):
    """
    Exports all LeadAnalysis data + full conversation logs to an Excel file.
    """
    from conversations.models import LeadAnalysis, Message
    from django.utils import timezone
    
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth.models import User

    # Authenticate via query param if accessed from a standard browser download link
    token = request.query_params.get("token")
    if token:
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            request.user = User.objects.get(id=user_id)
        except Exception as e:
            print(f"Token validation failed in export: {e}")

    if not request.user or not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=401)

    assigned_agent = None
    if hasattr(request.user, "profile"):
        assigned_agent = request.user.profile.assigned_agent

    is_super = request.user.is_superuser or not assigned_agent
    include_topic = request.user.is_superuser

    if is_super:
        leads = LeadAnalysis.objects.all().select_related('conversation', 'agent')
    else:
        leads = LeadAnalysis.objects.filter(agent=assigned_agent).select_related('conversation', 'agent')
    
    # Apply query filters if present
    lead_level = request.query_params.get("lead_level")
    agent_name = request.query_params.get("agent")
    call_type = request.query_params.get("call_type")
    date_filter = request.query_params.get("date_filter")

    include_missed = True

    if lead_level:
        if lead_level == "missed":
            leads = leads.none()
        else:
            leads = leads.filter(lead_level=lead_level)
            include_missed = False

    if agent_name:
        leads = leads.filter(agent__name=agent_name)
        include_missed = False

    if call_type:
        leads = leads.filter(conversation__call_type=call_type)
        if call_type == "INBOUND":
            include_missed = False

    date_start = None
    date_end = None
    if date_filter:
        import datetime
        now = timezone.now()
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        ist_now = now.astimezone(ist_tz)
        today_start = datetime.datetime(ist_now.year, ist_now.month, ist_now.day, tzinfo=ist_tz)
        
        if date_filter == "today":
            date_start = today_start
        elif date_filter == "yesterday":
            date_start = today_start - datetime.timedelta(days=1)
            date_end = today_start
        elif date_filter.startswith("custom_"):
            try:
                custom_val = date_filter.split("_")[1]
                parts = [int(p) for p in custom_val.split("-")]
                date_start = datetime.datetime(parts[0], parts[1], parts[2], tzinfo=ist_tz)
                date_end = date_start + datetime.timedelta(days=1)
            except Exception as e:
                print(f"Error parsing custom date in export: {e}")

        if date_start:
            if date_end:
                leads = leads.filter(analyzed_at__gte=date_start, analyzed_at__lt=date_end)
            else:
                leads = leads.filter(analyzed_at__gte=date_start)

    data = []
    for lead in leads:
        # Fetch and format transcript
        msgs = Message.objects.filter(conversation=lead.conversation).order_by('created_at')
        transcript = ""
        for m in msgs:
            role = "Bot" if m.role == "bot" else "User"
            transcript += f"[{role}]: {m.text}\n"
        
        # Normalize recording URL for export
        rec_url = ""
        try:
            if hasattr(lead.conversation, 'cdr') and lead.conversation.cdr:
                rec_url = lead.conversation.cdr.recording_file_name
                if rec_url and not rec_url.startswith("http"):
                    rec_url = f"https://app.voicelink.co.in/api/v1/add_lead{rec_url}"
        except:
            pass

        import datetime
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        analyzed_at_local = lead.analyzed_at.astimezone(ist_tz)

        data.append({
            "Analyzed At": analyzed_at_local.strftime("%Y-%m-%d %H:%M"),
            "Agent": lead.agent.name if lead.agent else "Unknown",
            # "Customer Name": lead.user_name or "Unknown",
            "Phone Number": lead.user_phone or lead.conversation.user_number,
            "Email": lead.user_email or "—",
            "Interest Level": lead.get_lead_level_display(),
            "Recording Link": rec_url,
            "AI Summary": lead.summary or "—",
            "Full Transcript": transcript.strip()
        })
        if include_topic:
            data[-1]["Topic"] = lead.interest_topic or "—"

    # 2. Add Missed Calls from the last campaign
    if include_missed:
        try:
            if is_super:
                status = CampaignStatus.objects.get(id=1)
                missed_list = json.loads(status.missed_calls) if status.missed_calls else []
                started_at = status.started_at
            else:
                # Get the last campaign run for the scoped agent
                last_campaign = Campaign.objects.filter(agent=assigned_agent).order_by("-started_at").first()
                if last_campaign:
                    missed_list = json.loads(last_campaign.missed_calls) if last_campaign.missed_calls else []
                    started_at = last_campaign.started_at
                else:
                    missed_list = []
                    started_at = None

            import datetime
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            
            # Apply date filter to missed calls started_at if date_start/date_end are defined
            if started_at:
                if date_start:
                    started_at_local = started_at.astimezone(ist_tz)
                    if date_end:
                        if not (date_start <= started_at_local < date_end):
                            missed_list = []
                    else:
                        if not (started_at_local >= date_start):
                            missed_list = []
            else:
                if date_start:
                    missed_list = []

            for phone in missed_list:
                if started_at:
                    try:
                        started_at_local = started_at.astimezone(ist_tz)
                        started_str = started_at_local.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        started_str = started_at.strftime("%Y-%m-%d %H:%M")
                else:
                    started_str = "—"

                data.append({
                    "Analyzed At": started_str,
                    "Agent": "Auto-Dialer",
                    # "Customer Name": "—",
                    "Phone Number": phone,
                    "Email": "—",
                    "Interest Level": "MISSED (No Answer)",
                    "Recording Link": "—",
                    "AI Summary": "The call was not picked up by the customer.",
                    "Full Transcript": "—"
                })
                if include_topic:
                    data[-1]["Topic"] = "Campaign Missed Call"
        except:
            pass
    
    if not data:
        # Return empty excel with headers if no leads
        columns = ["Analyzed At", "Agent", "Phone Number", "Email", "Interest Level"]
        if include_topic:
            columns.append("Topic")
        columns.extend(["Recording Link", "AI Summary", "Full Transcript"])
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(data)
        if not include_topic and "Topic" in df.columns:
            df = df.drop(columns=["Topic"])

    # Create Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lead Intelligence')
        
        # Auto-adjust column widths for readability
        worksheet = writer.sheets['Lead Intelligence']
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max() if not df[col].empty else 10, len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 60) # Cap at 60

    output.seek(0)
    
    filename = f"Lead_Analysis_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
def export_campaign_excel(request, campaign_id):
    """
    Exports all LeadAnalysis data, tries count, and conversation logs for a
    particular campaign (including all its retry attempts) to an Excel file.
    """
    from conversations.models import Conversation, LeadAnalysis, Message
    from bot.models import Campaign
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    from django.utils import timezone
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth.models import User
    import pandas as pd
    import io
    import json
    import datetime

    # Authenticate via query param if accessed from a standard browser download link
    token = request.query_params.get("token")
    if token:
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            request.user = User.objects.get(id=user_id)
        except Exception as e:
            print(f"Token validation failed in export: {e}")

    if not request.user or not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=401)

    # Fetch the campaign
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # Trace back to find the root parent campaign
    root_campaign = campaign
    while root_campaign.parent_campaign is not None:
        root_campaign = root_campaign.parent_campaign

    # Check permission on root campaign
    if not _is_campaign_visible_to_user(root_campaign, request.user):
        return Response({"error": "You do not have permission to export this campaign."}, status=403)

    # Find the campaign group (root campaign + all sub-campaign retries)
    campaigns = [root_campaign] + list(root_campaign.sub_campaigns.all().order_by("started_at"))
    campaign_ids = [c.id for c in campaigns]

    phone_list = json.loads(root_campaign.phone_list) if root_campaign.phone_list else []
    
    is_super = request.user.is_superuser or not hasattr(request.user, "profile") or not request.user.profile.assigned_agent

    data = []
    for phone in phone_list:
        clean_phone = _normalize_phone(phone)
        
        # Trace attempts and answer status across runs
        attempts = 0
        answered_attempt = None
        disposition = "Missed (No Answer)"
        
        for c in campaigns:
            c_phones = json.loads(c.phone_list) if c.phone_list else []
            c_phones_norm = [_normalize_phone(p) for p in c_phones]
            
            if clean_phone in c_phones_norm:
                attempts += 1
                c_missed = json.loads(c.missed_calls) if c.missed_calls else []
                c_missed_norm = [_normalize_phone(p) for p in c_missed]
                
                if clean_phone not in c_missed_norm:
                    # Answered in this run!
                    disposition = "Answered"
                    answered_attempt = attempts
                    break # Subsequent retries won't call this number
        
        # Fetch the Conversation matching this phone number and any of our campaign IDs
        # (Match using the last 10 digits to be safe with different formats)
        conv = Conversation.objects.filter(
            campaign_id__in=campaign_ids,
            user_number__icontains=clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
        ).order_by("-started_at").first()
        
        lead = None
        transcript = "—"
        rec_url = "—"
        lead_level_display = "MISSED (No Answer)"
        email = "—"
        summary = "The call was not picked up by the customer."
        topic = "Campaign Missed Call"
        analyzed_time_str = "—"
        
        if conv:
            # Transcript
            msgs = Message.objects.filter(conversation=conv).order_by('created_at')
            if msgs.exists():
                transcript_parts = []
                for m in msgs:
                    role = "Bot" if m.role == "bot" else "User"
                    transcript_parts.append(f"[{role}]: {m.text}")
                transcript = "\n".join(transcript_parts)
            
            # Recording URL
            try:
                if hasattr(conv, 'cdr') and conv.cdr:
                    rec_url = conv.cdr.recording_file_name
                    if rec_url and not rec_url.startswith("http"):
                        rec_url = f"https://app.voicelink.co.in/api/v1/add_lead{rec_url}"
            except Exception:
                pass
            
            # Lead Analysis
            try:
                lead = LeadAnalysis.objects.filter(conversation=conv).first()
                if lead:
                    lead_level_display = lead.get_lead_level_display()
                    email = lead.user_email or "—"
                    summary = lead.summary or "—"
                    topic = lead.interest_topic or "—"
                    
                    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                    analyzed_at_local = lead.analyzed_at.astimezone(ist_tz)
                    analyzed_time_str = analyzed_at_local.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        
        # If there was no LeadAnalysis, but the call was answered, update status info
        if disposition == "Answered":
            if lead_level_display == "MISSED (No Answer)":
                lead_level_display = "Answered (No details)"
            if summary == "The call was not picked up by the customer.":
                summary = "Call was answered but no analysis was generated."
            if topic == "Campaign Missed Call":
                topic = "—"
            if analyzed_time_str == "—" and conv:
                ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                started_local = conv.started_at.astimezone(ist_tz)
                analyzed_time_str = started_local.strftime("%Y-%m-%d %H:%M")
        
        picked_up_str = f"Attempt {answered_attempt}" if answered_attempt else "Never"
        
        row = {
            "Campaign Name": root_campaign.name or f"Campaign #{root_campaign.id}",
            "Phone Number": phone,
            "Status": disposition,
            "Total Attempts": attempts,
            "Picked Up On Attempt": picked_up_str,
            "Call Time (IST)": analyzed_time_str,
            "Interest Level": lead_level_display,
            "Recording Link": rec_url,
            "AI Summary": summary,
            "Full Transcript": transcript,
        }
        
        if is_super:
            row["Topic"] = topic
            
        data.append(row)

    if not data:
        columns = ["Campaign Name", "Phone Number", "Status", "Total Attempts", "Picked Up On Attempt", "Call Time (IST)", "Interest Level", "Recording Link", "AI Summary", "Full Transcript"]
        if is_super:
            columns.append("Topic")
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(data)

    # Create Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Campaign Report')
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Campaign Report']
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max() if not df[col].empty else 10, len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 60)

    output.seek(0)
    
    filename = f"Campaign_{root_campaign.id}_Report_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# Initialize campaign state from DB lazily when needed
_state_loaded = False

def _ensure_state_loaded():
    global _state_loaded
    if not _state_loaded:
        _load_campaign_state()
        _state_loaded = True


def trigger_retry_sub_campaign_if_needed(parent_campaign):
    """
    Spawns a deferred sub-campaign retry if the main campaign finishes and has missed calls,
    and hasn't exceeded the max retry attempts. All retry campaigns link directly to the root campaign.
    """
    from django.conf import settings
    max_retries = getattr(settings, "AUTO_CAMPAIGN_MAX_RETRIES", 5)
    retry_delay = getattr(settings, "AUTO_CAMPAIGN_RETRY_DELAY", 300)

    if parent_campaign.retry_count >= max_retries:
        print(f"AUTO-DIALER: Campaign #{parent_campaign.id} reached max retry limit ({max_retries}). Not retrying.")
        return

    missed_list = json.loads(parent_campaign.missed_calls) if parent_campaign.missed_calls else []
    if not missed_list:
        print(f"AUTO-DIALER: Campaign #{parent_campaign.id} has no missed calls. No retry needed.")
        return

    # Trace back to find the root parent campaign
    root_campaign = parent_campaign
    while root_campaign.parent_campaign is not None:
        root_campaign = root_campaign.parent_campaign

    print(f"AUTO-DIALER: Campaign #{parent_campaign.id} has {len(missed_list)} missed calls. Scheduling Retry #{parent_campaign.retry_count + 1} in {retry_delay} seconds...")

    try:
        retry_camp = Campaign.objects.create(
            name=f"Retry {parent_campaign.retry_count + 1} — {root_campaign.name}",
            phone_list=json.dumps(missed_list),
            total_count=len(missed_list),
            is_active=False,
            created_by=parent_campaign.created_by,
            agent=parent_campaign.agent,
            parent_campaign=root_campaign,
            retry_count=parent_campaign.retry_count + 1,
        )
    except Exception as e:
        print(f"WARNING: Failed to create retry Campaign record: {e}")
        return

    def run_retry():
        global _campaign_active, _campaign_paused, _current_campaign_id, _call_queue, _active_calls, _answered_calls, _missed_calls, BOT_URL
        
        if _campaign_active:
            print(f"⏳ AUTO-DIALER: Retry campaign #{retry_camp.id} is waiting because another campaign is running. Checking again in 15s...")
            import threading
            threading.Timer(15.0, run_retry).start()
            return

        print(f"🔥 AUTO-DIALER: Auto-triggering retry campaign #{retry_camp.id} (Parent #{parent_campaign.id})")
        
        agent_id = str(retry_camp.agent.id) if retry_camp.agent else "default"
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(BOT_URL)
            domain = parsed.netloc
            ws_scheme = parsed.scheme or "wss"
        except Exception:
            domain = "unprecious-waltraud-nasological.ngrok-free.dev"
            ws_scheme = "wss"
            
        BOT_URL = f"{ws_scheme}://{domain}/ws/voice-bot/service2/?agent_id={agent_id}"

        with _call_queue_lock:
            _call_queue.clear()
            _active_calls.clear()
            _answered_calls.clear()
            _missed_calls.clear()
            
            _call_queue.extend(missed_list)
            _campaign_active = True
            _campaign_paused = False
            _current_campaign_id = retry_camp.id
            
            _campaign_stats["total"] = len(missed_list)
            _campaign_stats["completed"] = 0
            _campaign_stats["started_at"] = timezone.now().isoformat()
            
            retry_camp.is_active = True
            retry_camp.started_at = timezone.now()
            retry_camp.save()
            
            _save_campaign_state()
            
        dial_next_from_queue()

    import threading
    threading.Timer(float(retry_delay), run_retry).start()


def _finalize_campaign():
    """Close the active Campaign history record with final stats."""
    global _current_campaign_id
    if not _current_campaign_id:
        return
    try:
        campaign = Campaign.objects.get(id=_current_campaign_id)
        campaign.is_active = False
        campaign.suspended_due_to_hours = False
        campaign.ended_at = timezone.now()
        campaign.completed_count = _campaign_stats.get("completed", 0)
        campaign.answered_count = max(0, campaign.completed_count - len(_missed_calls))
        campaign.missed_calls = json.dumps(_missed_calls)
        campaign.answered_calls = json.dumps(list(_answered_calls))
        campaign.save()
        print(f"AUTO-DIALER: Campaign #{campaign.id} finalized. Answered: {campaign.answered_count}, Missed: {len(_missed_calls)}")
        
        # Trigger retry sub-campaign if needed
        trigger_retry_sub_campaign_if_needed(campaign)
    except Exception as e:
        print(f"WARNING: Failed to finalize Campaign record: {e}")
    finally:
        _current_campaign_id = None


# =========================================================
# CAMPAIGN HISTORY PAGE & API (Admin Only)
# =========================================================

def campaign_history_page(request):
    return render(request, "campaign_history.html")


@api_view(["GET"])
def campaign_history_data(request):
    """Returns all past campaigns with stats for the admin dashboard."""
    campaigns = Campaign.objects.filter(parent_campaign__isnull=True).order_by("-started_at")
    campaigns = [c for c in campaigns if _is_campaign_visible_to_user(c, request.user)]

    def serialize_campaign(c):
        missed_list = json.loads(c.missed_calls) if c.missed_calls else []
        phone_list = json.loads(c.phone_list) if c.phone_list else []
        
        duration_seconds = None
        if c.ended_at and c.started_at:
            duration_seconds = int((c.ended_at - c.started_at).total_seconds())
            
        sub_camps = c.sub_campaigns.all().order_by("started_at")
        sub_serialized = [serialize_campaign(sub) for sub in sub_camps]
        
        return {
            "id": c.id,
            "name": c.name,
            "total_count": c.total_count,
            "completed_count": c.completed_count,
            "answered_count": c.answered_count,
            "missed_count": len(missed_list),
            "missed_list": missed_list,
            "phone_list": phone_list,
            "is_active": c.is_active,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "ended_at": c.ended_at.isoformat() if c.ended_at else None,
            "duration_seconds": duration_seconds,
            "created_by": c.created_by.username if c.created_by else None,
            "bot_name": c.agent.name if c.agent else None,
            "retry_count": c.retry_count,
            "suspended_due_to_hours": c.suspended_due_to_hours,
            "sub_campaigns": sub_serialized,
        }

    data = []
    for c in campaigns:
        data.append(serialize_campaign(c))
    
    # Summary stats (calculated over all visible campaigns including sub-campaigns)
    all_campaigns = Campaign.objects.all()
    all_visible = [c for c in all_campaigns if _is_campaign_visible_to_user(c, request.user)]
    
    total_campaigns = len(all_visible)
    total_calls = 0
    total_answered = 0
    total_missed = 0
    
    for c in all_visible:
        missed_list = json.loads(c.missed_calls) if c.missed_calls else []
        total_calls += c.total_count
        total_answered += c.answered_count
        total_missed += len(missed_list)
    
    return Response({
        "stats": {
            "total_campaigns": total_campaigns,
            "total_calls": total_calls,
            "total_answered": total_answered,
            "total_missed": total_missed,
        },
        "campaigns": data,
    })


@api_view(["GET"])
def download_sample_excel(request):
    """
    Generates and returns a sample Excel file containing 'name' and 'phone' columns.
    """
    import io
    import pandas as pd
    from django.http import HttpResponse

    # Create a simple DataFrame matching the user's requested format
    data = {
        "name": ["abc", "abc", "abc", "abc", "abc", "abc", "abc"],
        "phone": ["9979xxxxx", "972777xxxxx", "982538xxxx", "982522xxxx", "982522xxxx", "972777xxxx", "909901xxxx"]
    }
    df = pd.DataFrame(data)

    # Write DataFrame to an in-memory buffer as an Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    output.seek(0)

    # Set up HTTP response with correct content type and filename
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=sample_call_format.xlsx"
    return response


from django.views.decorators.csrf import csrf_exempt
from agents.models import VoiceAgent

@csrf_exempt
def inbound_call_webhook(request):
    """
    Webhook handler for incoming voice calls. Resolves the agent mapped to the dialed number
    and returns TwiML instructions to stream audio over WebSockets to our Channels consumer.
    """
    # 1. Parse dialed number (To) and caller number (From)
    to_number = request.POST.get("To") or request.GET.get("To") or ""
    from_number = request.POST.get("From") or request.GET.get("From") or ""

    if not to_number:
        import json
        try:
            body = json.loads(request.body.decode("utf-8"))
            to_number = body.get("to") or body.get("To") or ""
            from_number = body.get("from") or body.get("From") or ""
        except:
            pass

    def normalize(num):
        num_str = "".join(filter(str.isdigit, str(num)))
        if num_str.startswith("91") and len(num_str) == 12:
            num_str = num_str[2:]
        if num_str.startswith("0"):
            num_str = num_str[1:]
        return num_str

    normalized_to = normalize(to_number)
    normalized_from = normalize(from_number) or "unknown"

    print(f"[CALL] Incoming Call Webhook | Dialed (To): {to_number} (Normalized: {normalized_to}) | Caller (From): {from_number} (Normalized: {normalized_from})")

    # 2. Look up the active agent mapped to this incoming number
    agent = VoiceAgent.objects.filter(inbound_phone_number=normalized_to, is_active=True).first()

    # Fallback to checking with prefix "91" if not found
    if not agent and not to_number.startswith("91"):
        normalized_to_with_prefix = "91" + normalized_to
        agent = VoiceAgent.objects.filter(inbound_phone_number=normalized_to_with_prefix, is_active=True).first()

    # 3. Handle bot matching
    if agent:
        # Check if the agent has remaining call credit quota
        if not has_remaining_minutes(str(agent.id)):
            print(f"[WARNING] Inbound Call Rejected: Agent {agent.name} ({agent.id}) has exceeded call credits.")
            rejection_twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<Response>\n'
                '    <Say language="en-IN">Sorry, the service quota has been exceeded for this assistant.</Say>\n'
                '    <Hangup/>\n'
                '</Response>'
            )
            return HttpResponse(rejection_twiml, content_type="text/xml")

        # Determine language code based on agent industry or default
        language = "en"
        if agent.industry and agent.industry.slug in ["reminder-industry", "temp-real-estate"]:
            language = "gu"
        elif agent.industry and agent.industry.slug == "automobile":
            language = "hi"

        # Build secure WebSocket URL dynamically based on the current host header
        scheme = "wss" if request.is_secure() or request.headers.get("x-forwarded-proto") == "https" else "ws"
        host = request.get_host()
        
        ws_url = f"{scheme}://{host}/ws/voice-bot/service2/?agent_id={agent.id}&language={language}&phone={normalized_from}&call_type=INBOUND"
        print(f"[WS] Inbound Call Routing: Connected caller {normalized_from} to agent {agent.name} ({agent.id}) via WS: {ws_url}")

        escaped_ws_url = ws_url.replace("&", "&amp;")
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Response>\n'
            '    <Connect>\n'
            f'        <Stream url="{escaped_ws_url}" />\n'
            '    </Connect>\n'
            '</Response>'
        )
        return HttpResponse(twiml, content_type="text/xml")

    else:
        # Return fallback/rejection TwiML XML
        print(f"[ERROR] Inbound Call Rejected: No active agent found matching incoming number: {to_number}")
        fallback_twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Response>\n'
            '    <Say language="en-IN">Sorry, no assistant is configured for this number.</Say>\n'
            '    <Hangup/>\n'
            '</Response>'
        )
        return HttpResponse(fallback_twiml, content_type="text/xml")


def pre_synthesize_greeting(agent_id, phone, name, language="hi"):
    try:
        import os
        import json
        import audioop
        import numpy as np
        from elevenlabs import ElevenLabs, VoiceSettings
       
        # Clean phone to 10 digits
        clean_phone = "".join(filter(str.isdigit, str(phone)))[-10:]
        if not clean_phone:
            return
           
        file_path = os.path.join("mp3_responses", f"pre_synthesized_{agent_id}_{clean_phone}.raw")
        if os.path.exists(file_path):
            print(f"🎯 [PRE-SYNTHESIS]: Cached greeting already exists for {clean_phone}")
            return
           
        # Determine language code & greeting text
        if language == "gu":
            text = f"નમસ્તે! હું આઈશા બોલું છું, વેસ્ટકોસ્ટ કિયા તરફથી. આશા છે કે તમે મજામાં હશો! શું મારી વાત {name} સાથે થઈ રહી છે?"
        elif language == "en":
            text = f"Hello! I am Aaisha from Westcoast Kia. Hope you are doing well! Am I speaking with {name}?"
        else:
            text = f"Hello! Namaste... main Aaisha bol rahi hoon, West-coast Kia se. Umeed hai aap bilkul theek honge! Kya meri baat {name} se ho rahi hai?"
 
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("❌ [PRE-SYNTHESIS]: ELEVENLABS_API_KEY is missing. Cannot pre-synthesize.")
            return
           
        client = ElevenLabs(api_key=api_key)
        voice_id = "aSFxChEgBmCyExpaDqHd" # Kanika (same voice as consumers.py)
       
        print(f"🎙️ [PRE-SYNTHESIS START]: Synthesizing for name '{name}' and phone '{clean_phone}' using ElevenLabs...")
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="pcm_8000",
            voice_settings=VoiceSettings(
                stability=0.55,
                similarity_boost=0.75,
                style=0.00,
                use_speaker_boost=False,
                speed=1.00
            )
        )
       
        pcm = b""
        for chunk in audio_generator:
            if chunk:
                pcm += chunk
               
        if pcm:
            if len(pcm) % 2 != 0:
                pcm = pcm[:-1]
               
            # Gain amplification
            data = np.frombuffer(pcm, dtype=np.int16)
            data = (data * 0.6).clip(-32768, 32767).astype(np.int16)
            ulaw = audioop.lin2ulaw(data.tobytes(), 2)
           
            # Save raw file atomically via temp file to avoid race condition
            temp_file_path = file_path + ".tmp"
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            with open(temp_file_path, "wb") as f:
                f.write(ulaw)
            os.replace(temp_file_path, file_path)
            print(f"💾 [PRE-SYNTHESIS SUCCESS]: Pre-synthesized dynamic greeting saved: {file_path} ({len(ulaw)} bytes)")
        else:
            print("❌ [PRE-SYNTHESIS]: Empty audio returned from ElevenLabs.")
    except Exception as e:
        print(f"❌ [PRE-SYNTHESIS ERROR]: {e}")