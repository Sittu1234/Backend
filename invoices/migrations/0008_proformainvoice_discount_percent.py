from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0007_invoiceitem_remark"),
    ]

    operations = [
        migrations.AddField(
            model_name="proformainvoice",
            name="discount_percent",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
