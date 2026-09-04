from django.db import migrations


def fill_employee_ids(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    n = 1
    for user in User.objects.order_by("id"):
        if user.employee_id:
            continue
        while User.objects.filter(employee_id=f"KT{n:03d}").exists():
            n += 1
        user.employee_id = f"KT{n:03d}"
        user.save(update_fields=["employee_id"])
        n += 1


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_employee_id"),
    ]

    operations = [
        migrations.RunPython(fill_employee_ids, noop),
    ]
