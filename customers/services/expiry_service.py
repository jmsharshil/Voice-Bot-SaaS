
from datetime import date, timedelta
from customers.models import Customer


def get_expiring_customers():
    """
    Returns renewal customers whose policy expires within 5 days
    and haven't been reminded yet.
    """
    today = date.today()
    limit = today + timedelta(days=5)

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