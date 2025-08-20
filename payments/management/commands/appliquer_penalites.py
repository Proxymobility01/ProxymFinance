# payments/management/commands/appliquer_penalites.py
from django.core.management.base import BaseCommand
from payments.utils import appliquer_penalites_du_jour  # ✅ import CORRECT

class Command(BaseCommand):
    help = "Applique les pénalités du jour (après 12:01 Africa/Douala), idempotent."

    def handle(self, *args, **options):
        created = appliquer_penalites_du_jour(user=None)
        self.stdout.write(self.style.SUCCESS(f"{created} pénalité(s) appliquée(s)."))
