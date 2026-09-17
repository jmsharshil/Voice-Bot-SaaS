# # from datetime import date, timedelta
# # from bot.models import Customer

# # def get_expiring_customers():
# #     customers = Customer.objects.all()   # 🔥 TEMP FIX
# #     print("TOTAL CUSTOMERS:", customers)
# #     return customers



# from datetime import date, timedelta
# from bot.models import Customer

# def get_expiring_customers():

#     today = date.today()
#     limit = today + timedelta(days=5)   # 🔥 5 days window

#     # 🔥 DEBUG START
#     print("TODAY:", today)
#     print("LIMIT:", limit)

#     print("\nALL CUSTOMERS:")
#     for c in Customer.objects.all():
#         print(c.name, c.expiry_date)
#     # 🔥 DEBUG END

#     customers = Customer.objects.filter(
#         expiry_date__gte=today,     # not expired
#         expiry_date__lte=limit,     # within 5 days
#         reminder_sent=False         # not already sent
#     )

#     print("EXPIRING CUSTOMERS:", list(customers))

#     return customers



# # def get_expiring_customers():
# #     from bot.models import Customer

# #     customers = Customer.objects.all()   # 🔥 TEMP
# #     print("TOTAL CUSTOMERS:", customers)

# #     return customers









# ============================================================
#  bot/services/expiry_service.py
# ============================================================

from datetime import date, timedelta
from bot.models import Customer


def get_expiring_customers():
    """
    Returns renewal customers whose policy expires within 5 days
    and haven't been reminded yet.
    """
    today = date.today()
    limit = today + timedelta(days=15)

    print(f"[expiry_service] Checking renewals: {today} → {limit}")

    customers = Customer.objects.filter(
        customer_type="renewal",
        expiry_date__gte=today,
        expiry_date__lte=limit,
        reminder_sent=False,
    )

    print(f"[expiry_service] Expiring customers: {list(customers)}")
    return customers


def get_new_insurance_customers():
    """
    Returns new customers (no existing policy) who haven't been
    contacted yet.
    """
    print("[expiry_service] Fetching new insurance customers …")

    customers = Customer.objects.filter(
        customer_type="new",
        reminder_sent=False,
    )

    print(f"[expiry_service] New insurance customers: {list(customers)}")
    return customers


# ✅ NEW: returns customers whose policy has already expired (date < today)
def get_expired_customers():
    """
    Returns outbound renewal customers whose policy has already
    expired (expiry_date < today) and haven't been reminded yet.
    """
    today = date.today()

    print(f"[expiry_service] Checking expired policies before: {today}")

    customers = Customer.objects.filter(
        customer_type="renewal",
        source="outbound",
        expiry_date__lt=today,       # strictly before today = already expired
        reminder_sent=False,
    )

    print(f"[expiry_service] Expired customers: {list(customers)}")
    return customers