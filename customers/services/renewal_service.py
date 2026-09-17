import time

from customers.services.expiry_service import get_expiring_customers, get_new_insurance_customers
from bot.services.whatsapp_service import send_whatsapp_message
from customers.models import ChatMessage


# ── Message templates ──────────────────────────────────────────────────────────

RENEWAL_TEMPLATE = (
    "Hello {name} 👋\n\n"
    "Your *{vehicle_type}* insurance policy "
    "({vehicle_number}) is expiring on *{expiry_date}*.\n\n"
    "Would you like to renew it? (Yes / No)"
)

NEW_INSURANCE_TEMPLATE = (
    "Hello {name} 👋\n\n"
    "We noticed your *{vehicle_type}* ({vehicle_number}) "
    "doesn't have insurance yet! 🚨\n\n"
    "Driving without insurance is illegal and risky.\n\n"
    "Can I help you get covered today? (Yes / No) ✅"
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _send_and_log(customer, message: str) -> None:
    send_whatsapp_message(customer.phone, message)
    ChatMessage.objects.create(customer=customer, message=message, sender="bot")
    customer.reminder_sent = True
    customer.save()


# ── Public API ─────────────────────────────────────────────────────────────────

def run_renewal():
    """
    Send renewal reminders to expiring-policy customers.
    Called by /run-renewal/ endpoint or scheduled task.
    """
    customers = get_expiring_customers()
    print(f"[renewal_service] Renewal customers to contact: {len(customers)}")

    for c in customers:
        message = RENEWAL_TEMPLATE.format(
            name=c.name,
            vehicle_type=c.vehicle_type,
            vehicle_number=c.vehicle_number or "N/A",
            expiry_date=c.expiry_date,
        )
        print(f"[renewal_service] Sending renewal to {c.phone}")
        _send_and_log(c, message)
        time.sleep(2)


def run_new_insurance():
    """
    Send first-time insurance pitch to uninsured customers.
    Called by /run-new-insurance/ endpoint or scheduled task.
    """
    customers = get_new_insurance_customers()
    print(f"[renewal_service] New insurance customers to contact: {len(customers)}")

    for c in customers:
        message = NEW_INSURANCE_TEMPLATE.format(
            name=c.name,
            vehicle_type=c.vehicle_type,
            vehicle_number=c.vehicle_number or "N/A",
        )
        print(f"[renewal_service] Sending new insurance pitch to {c.phone}")
        _send_and_log(c, message)
        time.sleep(2)


def run_all():
    """Run both renewal and new insurance campaigns in one shot."""
    run_renewal()
    run_new_insurance()
