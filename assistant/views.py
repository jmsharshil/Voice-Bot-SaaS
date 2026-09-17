# from django.shortcuts import render

# # Create your views here.
from django.shortcuts import render

def home(request):
    return render(request, "dashboard.html")

def dashboard_view(request):
    return render(request, "dashboard.html")

def upload_view(request):
    return render(request, "upload.html")
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from django.core.files.storage import default_storage
import pandas as pd

from customers.models import Customer, ChatMessage


# ============================================================
# UI VIEWS
# ============================================================

def dashboard_view(request):
    return render(request, "dashboard.html")


def upload_view(request):
    return render(request, "upload.html")


# ============================================================
# DASHBOARD API
# ============================================================

@api_view(["GET"])
def dashboard_data(request):
    customers = Customer.objects.all()

    return Response({
        "total_customers": customers.count(),
        "total_messages": ChatMessage.objects.count(),
        "total_conversations": customers.count(),
        "total_outbound": customers.filter(source="outbound").count(),
        "total_inbound": customers.filter(source="inbound").count(),
    })


@api_view(["GET"])
def get_messages(request, customer_id):
    messages = ChatMessage.objects.filter(customer_id=customer_id).order_by("timestamp")

    return Response({
        "messages": [
            {
                "message": m.message,
                "sender": m.sender,
                "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
            for m in messages
        ]
    })


@api_view(["POST"])
def send_message_dashboard(request):
    customer_id = request.data.get("customer_id")
    message = request.data.get("message")

    if not customer_id or not message:
        return Response({"error": "Missing data"}, status=400)

    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

    # ✅ WhatsApp send
    from bot.services.whatsapp_service import send_whatsapp_message
    send_whatsapp_message(customer.phone, message)

    # ✅ Save message
    ChatMessage.objects.create(
        customer=customer,
        message=message,
        sender="bot"
    )

    return Response({"status": "sent"})


# ============================================================
# FILE UPLOAD API
# ============================================================

@api_view(["POST"])
def upload_file(request):
    file = request.FILES.get("file")

    if not file:
        return Response({"error": "No file"}, status=400)

    file_path = default_storage.save(file.name, file)

    df = pd.read_excel(file)

    for _, row in df.iterrows():
        Customer.objects.create(
            name=row.get("name", "User"),
            phone=str(row.get("phone")),
            vehicle_type=row.get("vehicle_type", "Car"),
            vehicle_number=row.get("vehicle_number"),
            customer_type=row.get("customer_type", "new"),
            source="outbound"
        )

    return Response({"status": "uploaded"})


@api_view(["GET"])
def get_upload_progress(request):
    return Response({"progress": 100})  # simple placeholder



@api_view(["POST"])
def whatsapp_webhook(request):
    print("📩 Webhook received:", request.data)

    return Response({"status": "received"})