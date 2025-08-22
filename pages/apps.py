from django.apps import AppConfig
# from django_q.models import Schedule
# from .tasks import send_weekly_summary
# from datetime import timedelta,timezone


class PagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'


# # Run every Monday at 9 AM
# Schedule.objects.create(
#     func='.tasks.send_weekly_summary',
#     schedule_type=Schedule.WEEKLY,
#     repeats=-1,  # repeat forever
#     next_run=timezone.now() + timedelta(seconds=10)  # test run first
# )
