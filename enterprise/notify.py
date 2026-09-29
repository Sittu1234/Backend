from django.core.mail import send_mail
from django.conf import settings

from activity.utils import log_activity
from .models import Notification


def notify(user, kind, title, body="", link="", whatsapp_hint="", request=None):
    if not user:
        return None
    n = Notification.objects.create(
        user=user,
        kind=kind,
        title=title,
        body=body,
        link=link,
        whatsapp_hint=whatsapp_hint,
    )
    if getattr(user, "email", None):
        try:
            send_mail(
                subject=f"SPARS ERP · {title}",
                message=body or title,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            n.email_sent = True
            n.save(update_fields=["email_sent"])
        except Exception:
            pass
    if request:
        log_activity(request.user, "notify", "Notification", n.id, title, request)
    return n
