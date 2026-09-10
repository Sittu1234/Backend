from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0005_alter_tax_invoice_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="proformainvoice",
            name="advance_received",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
