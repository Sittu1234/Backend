from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "employee_id",
            "role",
            "mobile",
            "manager",
            "linked_dealer",
            "is_active",
            "last_login",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "last_login")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    employee_id = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "employee_id",
            "role",
            "mobile",
            "manager",
            "linked_dealer",
            "password",
            "is_active",
        )

    def validate_employee_id(self, value):
        value = (value or "").strip().upper()
        if not value:
            return value
        qs = User.objects.filter(employee_id__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This Employee ID is already in use.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})
        employee_id = (validated_data.pop("employee_id", None) or "").strip().upper()
        if not employee_id:
            employee_id = User.next_employee_id()
        return User.objects.create_user(password=password, employee_id=employee_id, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        employee_id = validated_data.pop("employee_id", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if employee_id is not None:
            employee_id = employee_id.strip().upper()
            instance.employee_id = employee_id or instance.employee_id
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_blank=True)
    login = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField()
    role = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        ident = (attrs.get("login") or attrs.get("email") or "").strip()
        if not ident:
            raise serializers.ValidationError({"email": "Email or Employee ID is required."})
        attrs["ident"] = ident
        role = (attrs.get("role") or "").strip().lower()
        allowed = ("admin", "sales", "accountant", "hr", "manager", "technician", "dealer")
        if role and role not in allowed:
            raise serializers.ValidationError({"role": "Select a valid login role."})
        attrs["role"] = role
        return attrs


class DealerRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    company_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    mobile = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=8, write_only=True)
    city = serializers.CharField(max_length=80)
    state = serializers.CharField(max_length=80)
    pincode = serializers.CharField(max_length=10, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    gst_no = serializers.CharField(max_length=15, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered. Use dealer login.")
        return value

    def validate_mobile(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 10:
            raise serializers.ValidationError("Enter a valid 10-digit mobile number.")
        return digits[-10:]

    def validate_gst_no(self, value):
        return (value or "").strip().upper()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)
