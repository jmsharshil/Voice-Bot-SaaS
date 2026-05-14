# Data migration: set existing walk-in customers (no batch) to source="inbound"

from django.db import migrations


def fix_existing_sources(apps, schema_editor):
    Customer = apps.get_model('bot', 'Customer')
    # Customers with no batch are walk-ins (inbound)
    # Only update those currently source="outbound" (the old default)
    Customer.objects.filter(
        batch__isnull=True,
        source="outbound",
    ).update(source="inbound")


def reverse(apps, schema_editor):
    Customer = apps.get_model('bot', 'Customer')
    Customer.objects.filter(
        batch__isnull=True,
        source="inbound",
    ).update(source="outbound")


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0010_customer_source_alter_customer_phone_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_existing_sources, reverse),
    ]
