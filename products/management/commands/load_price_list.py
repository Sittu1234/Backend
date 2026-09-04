from django.core.management.base import BaseCommand

from products.catalog import sync_today_price_list


class Command(BaseCommand):
    help = "Load today's Kalpna Traders price list: EV scooter, lithium battery, LED battery"

    def handle(self, *args, **options):
        result = sync_today_price_list()
        self.stdout.write(
            self.style.SUCCESS(
                f"Today price list ready. Created {result['created']}, updated {result['updated']}."
            )
        )
