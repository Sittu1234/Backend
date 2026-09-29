from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        if not extra.get("employee_id"):
            extra["employee_id"] = User.next_employee_id()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", User.Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin / MD"
        SALES = "sales", "Sales Executive"
        ACCOUNTANT = "accountant", "Accountant"
        HR = "hr", "HR"
        MANAGER = "manager", "Manager"
        TECHNICIAN = "technician", "Technician"
        DEALER = "dealer", "Dealer Portal"

    STAFF_ROLES = (
        Role.ADMIN,
        Role.SALES,
        Role.ACCOUNTANT,
        Role.HR,
        Role.MANAGER,
        Role.TECHNICIAN,
    )

    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SALES, db_index=True)
    mobile = models.CharField(max_length=15, blank=True)
    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_members",
    )
    linked_dealer = models.ForeignKey(
        "customers.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="portal_users",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.employee_id or self.email})"

    @classmethod
    def next_employee_id(cls):
        ids = cls.objects.exclude(employee_id__isnull=True).values_list("employee_id", flat=True)
        nums = []
        for eid in ids:
            if eid and eid.upper().startswith("KT") and eid[2:].isdigit():
                nums.append(int(eid[2:]))
        n = max(nums) + 1 if nums else 1
        return f"KT{n:03d}"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_sales(self):
        return self.role == self.Role.SALES

    @property
    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT

    @property
    def is_hr(self):
        return self.role == self.Role.HR

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_technician(self):
        return self.role == self.Role.TECHNICIAN

    @property
    def is_dealer(self):
        return self.role == self.Role.DEALER

    @property
    def is_internal(self):
        return self.role != self.Role.DEALER


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at
