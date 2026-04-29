from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remplit AllAssets.name depuis Yahoo (yfinance) quand le nom est vide ou égal au symbole."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500, help="Nombre max de lignes à traiter")
        parser.add_argument("--dry-run", action="store_true", help="Ne modifie pas la base, affiche seulement")

    def handle(self, *args, **options):
        from apps.trading.models import AllAssets
        from apps.trading.services.data_providers.yahoo_finance import YahooFinanceService

        limit = int(options["limit"] or 500)
        dry_run = bool(options["dry_run"])

        service = YahooFinanceService()
        if not service.is_available:
            self.stderr.write(self.style.ERROR("yfinance not available on server"))
            return

        qs = (
            AllAssets.objects.exclude(symbole_yahoo__in=["Not_searched", "not_found", "manual", ""])
            .order_by("id")[: max(1, limit)]
        )

        checked = 0
        updated = 0

        for asset in qs:
            checked += 1
            current_name = (asset.name or "").strip()
            symbol_like = (asset.symbol or "").strip()

            if current_name and current_name.lower() != symbol_like.lower():
                continue

            new_name = service.get_display_name(asset.symbole_yahoo)
            if not new_name:
                continue

            if dry_run:
                self.stdout.write(f"[DRY] {asset.id} {asset.symbol} -> {new_name}")
            else:
                asset.name = new_name
                asset.save(update_fields=["name", "last_updated"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. checked={checked} updated={updated} dry_run={dry_run}"))

