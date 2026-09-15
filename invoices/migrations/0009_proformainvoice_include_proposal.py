from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0008_proformainvoice_discount_percent"),
    ]

    operations = [
        migrations.AddField(
            model_name="proformainvoice",
            name="include_proposal",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="proformainvoice",
            name="proposal_note",
            field=models.TextField(blank=True),
        ),
    ]
