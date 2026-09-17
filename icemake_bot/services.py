import logging
import re
from django.db.models import Q

logger = logging.getLogger(__name__)

def clean_phone_number(raw_phone: str) -> str:
    """Extracts last 10 digits of a phone number."""
    if not raw_phone:
        return ""
    digits = "".join(filter(str.isdigit, str(raw_phone)))
    return digits[-10:] if len(digits) >= 10 else digits

def get_customer_prefill_data(raw_phone: str) -> dict:
    """
    Searches pre-uploaded Customer records or previous IcemakeTicket records
    to fetch pre-filled customer details by phone number.
    Returns a dictionary of pre-filled fields.
    """
    clean_p = clean_phone_number(raw_phone)
    if not clean_p:
        return {}

    prefill_data = {
        "customer_name": "",
        "company_name": "",
        "city_state": "",
        "machine_model_no": "",
        "machine_sr_no": "",
        "registered_mobile": raw_phone or clean_p,
        "is_prefilled": False,
    }

    # 1. Search in bot.models.Customer (from Excel upload)
    try:
        from bot.models import Customer
        customer = Customer.objects.filter(phone__icontains=clean_p).order_by("-id").first()
        if customer:
            prefill_data["customer_name"] = customer.name if customer.name and customer.name != "User" else ""
            
            machine_model = getattr(customer, "vehicle_model", "") or getattr(customer, "policy_type", "")
            if machine_model:
                prefill_data["machine_model_no"] = machine_model
                
            city = getattr(customer, "city", "") or getattr(customer, "state", "")
            if city:
                prefill_data["city_state"] = city

            company = getattr(customer, "company_name", "") or getattr(customer, "company", "")
            if company:
                prefill_data["company_name"] = company

            sr_no = getattr(customer, "machine_sr_no", "") or getattr(customer, "serial_no", "")
            if sr_no:
                prefill_data["machine_sr_no"] = sr_no

            logger.info(f"[ICEMAKE PREFILL] Found Customer record for {clean_p}: {customer.name}")
    except Exception as e:
        logger.debug(f"[ICEMAKE PREFILL] Customer query notice: {e}")

    # 2. Search in previous IcemakeTicket records if any fields are still missing
    try:
        from icemake_bot.models import IcemakeTicket
        ticket = IcemakeTicket.objects.filter(registered_mobile__icontains=clean_p).order_by("-created_at").first()
        if ticket:
            if not prefill_data["customer_name"] and ticket.customer_name:
                prefill_data["customer_name"] = ticket.customer_name
            if not prefill_data["company_name"] and ticket.company_name:
                prefill_data["company_name"] = ticket.company_name
            if not prefill_data["city_state"] and ticket.city_state:
                prefill_data["city_state"] = ticket.city_state
            if not prefill_data["machine_model_no"] and ticket.machine_model_no:
                prefill_data["machine_model_no"] = ticket.machine_model_no
            if not prefill_data["machine_sr_no"] and ticket.machine_sr_no:
                prefill_data["machine_sr_no"] = ticket.machine_sr_no
            logger.info(f"[ICEMAKE PREFILL] Found past IcemakeTicket for {clean_p}: #{ticket.ticket_number}")
    except Exception as e:
        logger.debug(f"[ICEMAKE PREFILL] Ticket query notice: {e}")

    if prefill_data["customer_name"] or prefill_data["machine_model_no"] or prefill_data["city_state"]:
        prefill_data["is_prefilled"] = True

    return prefill_data
