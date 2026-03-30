from django.utils import timezone
from django.db import transaction
from .models import  Notification, Dropout

def my_daily_check_function():
    print("Action performed.")
    today = timezone.now().date()
    alerts = Dropout.objects.filter(
        followup_date=today
    ).select_related('enrollment', 'enrollment__student')

    if not alerts.exists():
        print("No follow-ups scheduled for this date.")
        return


    try:
        with transaction.atomic():
            for alert in alerts:
                student = alert.enrollment.student
                remark = alert.remark if alert.remark else "No remark provided"
                message = f"Follow-up Reminder: {student.full_name} is due for a check-in on {today}. Reason: {remark}"
                Notification.objects.create(
                    title="Upcoming Student Follow-up",
                    message=message,
                    student=student,
                    alert_type="FOLLOW_UP"
                )
        print(f"Successfully processed {alerts.count()} follow-up alerts.")

    except Exception as e:
        print(f"Error processing dropout follow-ups: {str(e)}")
