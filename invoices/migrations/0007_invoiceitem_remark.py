from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0006_proformainvoice_advance_received"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceitem",
            name="remark",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
