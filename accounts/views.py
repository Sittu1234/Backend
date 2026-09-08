import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from activity.utils import log_activity
from .models import PasswordResetToken, User
from .permissions import IsAdmin
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
)


def _find_user(ident: str):
    ident = ident.strip()
    qs = User.objects.filter(Q(email__iexact=ident) | Q(employee_id__iexact=ident))
    return qs.first()


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ident = serializer.validated_data["ident"]
    password = serializer.validated_data["password"]
    user = _find_user(ident)
    if not user or not user.is_active or not user.check_password(password):
        return Response({"detail": "Invalid Employee ID / email or password."}, status=400)
    wanted = (serializer.validated_data.get("role") or "").strip().lower()
    if wanted:
        actual = "admin" if user.is_admin else user.role
        if actual != wanted:
            labels = {"admin": "Admin", "sales": "Sales", "accountant": "Accountant"}
            return Response(
                {
                    "detail": (
                        f"This account is {labels.get(actual, actual)}. "
                        f"Select {labels.get(actual, actual)} from the login dropdown."
                    )
                },
                status=400,
            )
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    refresh = RefreshToken.for_user(user)
    log_activity(user, "login", "User", user.id, "User logged in")
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    refresh = request.data.get("refresh")
    if refresh:
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except Exception:
            pass
    return Response({"detail": "Logged out."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]
    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        return Response(
            {"detail": "If an account exists, a reset link has been sent."}
        )
    token = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=timezone.now() + timedelta(hours=2),
    )
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    send_mail(
        subject="SPARS ERP – Reset your password",
        message=(
            f"Hello {user.name},\n\n"
            f"Use the link below to reset your password (valid for 2 hours):\n"
            f"{reset_url}\n\n"
            f"If you did not request this, ignore this email.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    payload = {"detail": "If an account exists, a reset link has been sent."}
    if settings.DEBUG:
        payload["reset_url"] = reset_url
        payload["token"] = token
    return Response(payload)


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        record = PasswordResetToken.objects.select_related("user").get(
            token=serializer.validated_data["token"]
        )
    except PasswordResetToken.DoesNotExist:
        return Response({"detail": "Invalid or expired token."}, status=400)
    if not record.is_valid():
        return Response({"detail": "Invalid or expired token."}, status=400)
    user = record.user
    user.set_password(serializer.validated_data["password"])
    user.save()
    record.used = True
    record.save(update_fields=["used"])
    return Response({"detail": "Password updated. You can now log in."})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdmin]
    search_fields = ["name", "email", "employee_id", "mobile"]
    filterset_fields = ["role", "is_active"]
    ordering_fields = ["name", "created_at", "employee_id"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        log_activity(self.request.user, "create", "User", user.id, f"Created user {user.email}")

    def perform_update(self, serializer):
        user = serializer.save()
        log_activity(self.request.user, "update", "User", user.id, f"Updated user {user.email}")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.id == request.user.id:
            return Response({"detail": "You cannot delete your own account."}, status=400)
        log_activity(request.user, "delete", "User", instance.id, f"Deleted user {instance.email}")
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def roles(self, request):
        return Response([{"value": c[0], "label": c[1]} for c in User.Role.choices])

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def lookup(self, request):
        qs = User.objects.filter(is_active=True)
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return Response(UserSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def sales_team(self, request):
        qs = User.objects.filter(role=User.Role.SALES, is_active=True)
        return Response(UserSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get("password") or ""
        if len(password) < 8:
            return Response({"detail": "Password must be at least 8 characters."}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        log_activity(request.user, "update", "User", user.id, f"Reset password for {user.email}")
        return Response({"detail": f"Password updated for {user.name}."})
