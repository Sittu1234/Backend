from .models import ActivityLog


def log_activity(user, action, model_name, object_id=None, details="", request=None):
    ip = None
    if request:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
    ActivityLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else None,
        details=details,
        ip_address=ip,
    )
