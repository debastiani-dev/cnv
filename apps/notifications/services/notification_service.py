from apps.notifications.models import Notification


def create_notification(
    recipient, title, message, category=Notification.Category.INFO, link=""
):
    """
    Creates a new notification for a specific user.
    """
    return Notification.objects.create(
        recipient=recipient, title=title, message=message, category=category, link=link
    )
