# from django.core.mail import send_mail
# from django.conf import settings
# from .models import User, Funding_Request, UserRole, FundingRequestStatus

# def send_weekly_summary():
#     directors = User.objects.filter(role=UserRole.LUCIA_DIRECTOR)
#     pending_requests = Funding_Request.objects.filter(
#         status=FundingRequestStatus.PENDING_VETTING
#     )

#     if not pending_requests.exists():
#         return "No pending funding requests."

#     subject = "Weekly Summary: Pending Funding Requests"
#     body_lines = ["The following funding requests are pending review:\n"]

#     for fr in pending_requests:
#         body_lines.append(
#             f"- {fr.requesting_organization_name} requesting ${fr.amount_requested} for {fr.purpose}"
#         )

#     body = "\n".join(body_lines)

#     for director in directors:
#         send_mail(
#             subject,
#             body,
#             settings.DEFAULT_FROM_EMAIL,
#             [director.email],
#             fail_silently=False,
#         )

#     return "Weekly summary emails sent successfully."
