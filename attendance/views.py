from datetime import datetime

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsAdmin
from activity.utils import log_activity
from .models import Attendance
from .serializers import AttendanceSerializer


def _now():
    return timezone.localtime()


def _today():
    return _now().date()


def _now_time():
    return _now().time().replace(microsecond=0)


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["user", "date", "status"]
    ordering_fields = ["date", "check_in"]

    def get_queryset(self):
        qs = Attendance.objects.select_related("user", "marked_by")
        user = self.request.user
        if not user.is_admin:
            return qs.filter(user=user)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "mark"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        rec = serializer.save(marked_by=self.request.user)
        log_activity(
            self.request.user,
            "create",
            "Attendance",
            rec.id,
            f"Marked {rec.user.name} {rec.status} on {rec.date}",
        )

    @action(detail=False, methods=["post"])
    def check_in(self, request):
        today = _today()
        rec, created = Attendance.objects.get_or_create(
            user=request.user,
            date=today,
            defaults={
                "check_in": _now_time(),
                "status": Attendance.Status.PRESENT,
                "marked_by": request.user,
            },
        )
        if rec.check_in and not created:
            return Response(
                {"detail": "Already checked in today.", "attendance": AttendanceSerializer(rec).data},
                status=400,
            )
        if not rec.check_in:
            rec.check_in = _now_time()
            rec.status = Attendance.Status.PRESENT
            rec.marked_by = request.user
            rec.save(update_fields=["check_in", "status", "marked_by", "updated_at"])
        log_activity(request.user, "check_in", "Attendance", rec.id, f"Check-in {today}")
        return Response(AttendanceSerializer(rec).data)

    @action(detail=False, methods=["post"])
    def check_out(self, request):
        today = _today()
        rec = Attendance.objects.filter(user=request.user, date=today).first()
        if not rec or not rec.check_in:
            return Response({"detail": "Check in first."}, status=400)
        if rec.check_out:
            return Response(
                {"detail": "Already checked out today.", "attendance": AttendanceSerializer(rec).data},
                status=400,
            )
        rec.check_out = _now_time()
        rec.save(update_fields=["check_out", "updated_at"])
        log_activity(request.user, "check_out", "Attendance", rec.id, f"Check-out {today}")
        return Response(AttendanceSerializer(rec).data)

    @action(detail=False, methods=["get"])
    def today(self, request):
        rec = Attendance.objects.filter(user=request.user, date=_today()).first()
        return Response(AttendanceSerializer(rec).data if rec else None)

    @action(detail=False, methods=["get"], permission_classes=[IsAdmin])
    def roster(self, request):
        raw = request.query_params.get("date") or _today().isoformat()
        try:
            day = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            day = _today()
        staff = User.objects.filter(is_active=True).exclude(role=User.Role.ADMIN).order_by("name")
        records = {
            r.user_id: r
            for r in Attendance.objects.filter(date=day, user__in=staff).select_related("user", "marked_by")
        }
        rows = []
        for u in staff:
            rec = records.get(u.id)
            rows.append(
                {
                    "user": u.id,
                    "user_name": u.name,
                    "employee_id": u.employee_id,
                    "user_role": u.role,
                    "mobile": u.mobile,
                    "date": day.isoformat(),
                    "id": rec.id if rec else None,
                    "check_in": rec.check_in.strftime("%H:%M:%S") if rec and rec.check_in else None,
                    "check_out": rec.check_out.strftime("%H:%M:%S") if rec and rec.check_out else None,
                    "status": rec.status if rec else "unmarked",
                    "notes": rec.notes if rec else "",
                    "marked_by_name": rec.marked_by.name if rec and rec.marked_by else "",
                }
            )
        counts = {"present": 0, "absent": 0, "leave": 0, "half_day": 0, "unmarked": 0, "holiday": 0}
        for row in rows:
            key = row["status"] if row["status"] in counts else "unmarked"
            counts[key] += 1
        return Response({"date": day.isoformat(), "counts": counts, "rows": rows})

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def mark(self, request):
        user_id = request.data.get("user")
        raw_date = request.data.get("date") or _today().isoformat()
        status_val = request.data.get("status") or Attendance.Status.PRESENT
        notes = request.data.get("notes") or ""
        if status_val not in Attendance.Status.values:
            return Response({"detail": "Invalid status."}, status=400)
        try:
            day = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "Invalid date."}, status=400)
        try:
            staff = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=400)
        rec, _ = Attendance.objects.update_or_create(
            user=staff,
            date=day,
            defaults={
                "status": status_val,
                "notes": notes,
                "marked_by": request.user,
            },
        )
        if status_val == Attendance.Status.PRESENT and not rec.check_in:
            rec.check_in = _now_time()
            rec.save(update_fields=["check_in", "updated_at"])
        log_activity(
            request.user,
            "update",
            "Attendance",
            rec.id,
            f"Marked {staff.name} {status_val} on {day}",
        )
        return Response(AttendanceSerializer(rec).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        now = _now()
        year = int(request.query_params.get("year") or now.year)
        month = int(request.query_params.get("month") or now.month)
        qs = Attendance.objects.filter(date__year=year, date__month=month)
        if not request.user.is_admin:
            qs = qs.filter(user=request.user)
            staff = User.objects.filter(pk=request.user.pk)
        else:
            user_id = request.query_params.get("user")
            if user_id:
                qs = qs.filter(user_id=user_id)
            staff = User.objects.filter(is_active=True).exclude(role=User.Role.ADMIN)
        data = []
        for u in staff:
            uqs = qs.filter(user=u)
            data.append(
                {
                    "user": u.id,
                    "name": u.name,
                    "employee_id": u.employee_id,
                    "present": uqs.filter(status=Attendance.Status.PRESENT).count(),
                    "absent": uqs.filter(status=Attendance.Status.ABSENT).count(),
                    "leave": uqs.filter(status=Attendance.Status.LEAVE).count(),
                    "half_day": uqs.filter(status=Attendance.Status.HALF_DAY).count(),
                }
            )
        return Response({"year": year, "month": month, "rows": data})
