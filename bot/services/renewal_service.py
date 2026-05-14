# # from bot.services.expiry_service import get_expiring_customers
# # from bot.services.whatsapp_service import send_whatsapp_message

# # def run_renewal():

# #     customers = get_expiring_customers()

# #     for c in customers:

# #         message = f"""
# # Hello {c.name} 👋

# # Your {c.policy_type} policy will expire on {c.expiry_date}.

# # Please renew your policy.
# # """

# #         print(f"Sending to {c.phone}")

# #         send_whatsapp_message(c.phone, message)

# #         c.reminder_sent = True
# #         c.save()




# from bot.services.expiry_service import get_expiring_customers
# from bot.services.whatsapp_service import send_whatsapp_message
# from bot.models import ChatMessage
# import time

# def run_renewal():

#     customers = get_expiring_customers()

#     print("FINAL CUSTOMERS TO SEND:", customers)

#     for c in customers:

#         message = f"""
# Hello {c.name} 👋

# Your {c.policy_type} policy will expire on {c.expiry_date}.

# Do you want to renew your policy?
# """

#         print("Sending to:", c.phone)

#         send_whatsapp_message(c.phone, message)


#         ChatMessage.objects.create(
#             customer=c,
#             message=message,
#             sender="bot"
#         )

#         c.reminder_sent = True
#         c.save()

#         time.sleep(2)







# ============================================================
#  bot/services/renewal_service.py
# ============================================================

import time
from datetime import date

from bot.services.expiry_service import get_expiring_customers, get_new_insurance_customers, get_expired_customers
from bot.services.whatsapp_service import send_whatsapp_message
from bot.models import ChatMessage


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

# ✅ NEW: for policies that have already expired (date < today)
EXPIRED_TEMPLATE = (
    "Hello {name} 👋\n\n"
    "⚠️ Your *{vehicle_type}* insurance (*{vehicle_number}*) "
    "has *expired* on *{expiry_date}*.\n\n"
    "Driving without insurance is illegal and risky! 🚨\n\n"
    "Would you like to renew it now? (Yes / No)"
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


# ✅ NEW: send expired policy reminders
def run_expired():
    """
    Send urgent expired-policy messages to customers whose
    insurance has already lapsed (expiry_date < today).
    Called by /run-expired/ endpoint or scheduled task.
    """
    customers = get_expired_customers()
    print(f"[renewal_service] Expired policy customers to contact: {len(customers)}")

    for c in customers:
        message = EXPIRED_TEMPLATE.format(
            name=c.name,
            vehicle_type=c.vehicle_type,
            vehicle_number=c.vehicle_number or "N/A",
            expiry_date=c.expiry_date.strftime("%d-%m-%Y"),
        )
        print(f"[renewal_service] Sending expired notice to {c.phone} (expired {c.expiry_date})")
        _send_and_log(c, message)
        time.sleep(2)


def run_all():
    """Run renewal, expired, and new insurance campaigns in one shot."""
    run_expired()    # ✅ expired first — most urgent
    run_renewal()
    run_new_insurance()