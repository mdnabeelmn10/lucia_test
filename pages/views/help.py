from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings

@api_view(["POST"])
@permission_classes([AllowAny])  # or IsAuthenticated if you want login required
def help_form_view(request):
    name = request.data.get("name")
    email = request.data.get("email")
    message = request.data.get("message")
    to_email = "lucia.helpdesk1@gmail.com"  # default target email

    if not all([name, email, message]):
        return Response({"error": "Missing required fields."}, status=400)

    subject = f"Lucia Charitable - Help Form Submission from {name}"
    full_message = f"""
A new help request has been submitted through the Lucia Donor Dashboard.

From: {name}
Email: {email}

Message:
{message}
    """.strip()

    try:
        send_mail(
            subject=subject,
            message=full_message,
            from_email="lucia.helpdesk1@gmail.com",
            recipient_list=[to_email],
            fail_silently=False,
        )
        return Response({"status": "sent"})
    except Exception as e:
        return Response({"error": str(e)}, status=500)
