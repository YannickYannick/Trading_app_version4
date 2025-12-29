"""
Commande Django pour créer les brokers par défaut.
"""
from django.core.management.base import BaseCommand
from apps.trading.models import Broker


class Command(BaseCommand):
    help = 'Crée les brokers par défaut (Saxo Bank, Binance, etc.)'

    def handle(self, *args, **options):
        brokers_data = [
            {
                'name': 'Saxo Bank',
                'broker_type': Broker.BrokerType.SAXO,
                # ✅ MIGRATION: URL changée de SIM vers LIVE
                'api_base_url': 'https://gateway.saxobank.com/openapi',
                'api_version': 'v1',
                'is_active': True,
                'supports_stocks': True,
                'supports_crypto': True,
                'supports_forex': True,
                'supports_futures': True,
            },
            {
                'name': 'Binance',
                'broker_type': Broker.BrokerType.BINANCE,
                'api_base_url': 'https://api.binance.com',
                'api_version': 'v3',
                'is_active': True,
                'supports_stocks': False,
                'supports_crypto': True,
                'supports_forex': False,
                'supports_futures': True,
            },
            {
                'name': 'Interactive Brokers',
                'broker_type': Broker.BrokerType.INTERACTIVE_BROKERS,
                'api_base_url': '',
                'api_version': '',
                'is_active': True,
                'supports_stocks': True,
                'supports_crypto': False,
                'supports_forex': True,
                'supports_futures': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for broker_data in brokers_data:
            broker, created = Broker.objects.update_or_create(
                broker_type=broker_data['broker_type'],
                defaults=broker_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Broker créé: {broker.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'→ Broker mis à jour: {broker.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Terminé: {created_count} créé(s), {updated_count} mis à jour'
            )
        )

