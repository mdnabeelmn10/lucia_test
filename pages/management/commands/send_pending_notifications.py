from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from ...models import Donation, Vote, User, UserRole
from django.core.mail import EmailMultiAlternatives
from django.utils.html import format_html

class Command(BaseCommand):
    help = "Send daily email to directors if pending_review donations exist"

    def handle(self, *args, **kwargs):
        directors = User.objects.filter(role=UserRole.LUCIA_DIRECTOR)

        for director in directors:
            voted_ids = Vote.objects.filter(director=director).values_list("donation_id", flat=True)
            pending_donations = Donation.objects.filter(
                status="pending_review"
            ).exclude(id__in=voted_ids)

            if pending_donations.exists():
                rows = ""
                for d in pending_donations:
                    rows += f"""
                    <tr>
                        <td>{d.source_daf.name if d.source_daf else 'Anonymous'}</td>
                        <td>{d.recipient_charity.name if d.recipient_charity else 'Unknown Charity'}</td>
                        <td>${d.amount}</td>
                        <td>{d.purpose or 'N/A'}</td>
                    </tr>
                    """

                html_body = f"""
                <p>Hello {director.username},</p>
                <p>You have <b>{pending_donations.count()}</b> donation(s) pending review:</p>
                <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width:100%;">
                    <thead>
                        <tr style="background:#f2f2f2;">
                            <th>Donor</th>
                            <th>Charity</th>
                            <th>Amount</th>
                            <th>Purpose</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                <p>Please <a href = "https://lucia-dashboard-bd557027aebb.herokuapp.com/">log in</a> to the dashboard to review and vote.</p>
                <p>Thank you,<br>Lucia Team</p>
                """

                msg = EmailMultiAlternatives(
                    subject="Pending Donations Need Your Review",
                    body="Please view this email in HTML format.",
                    from_email="lucia.helpdesk1@gmail.com",
                    # to=["persnabeel@gmail.com"],
                    to=["mdnabeelmn10@gmail.com","shineyjeyaraj@gmail.com"],
                    # recipient_list=[director.email],

                )
                msg.attach_alternative(html_body, "text/html")
                msg.send()

        self.stdout.write(self.style.SUCCESS("Daily pending donation notifications sent."))
