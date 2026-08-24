"""
Synchronise les coûts de transaction Saxo (reports post-trade).

Usage:
    python manage.py sync_saxo_costs --from 2026-08-01 --to 2026-08-24
    python manage.py sync_saxo_costs --from 2026-08-01 --to 2026-08-24 --account-id 4
    python manage.py sync_saxo_costs --from 2026-08-01 --to 2026-08-24 --dry-run
"""
from datetime import date, datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from apps.trading.models import BrokerAccount
from apps.trading.services.saxo import SaxoCostService
from apps.trading.utils.user_utils import get_broker_account_or_error, get_user_or_error


class Command(BaseCommand):
    help = 'Rattrapage idempotent des coûts Saxo (reports/trades) vers TransactionCost'

    def add_arguments(self, parser):
        parser.add_argument('--from', dest='from_date', required=True, help='YYYY-MM-DD')
        parser.add_argument('--to', dest='to_date', required=True, help='YYYY-MM-DD')
        parser.add_argument('--user-id', type=int)
        parser.add_argument('--account-id', type=int)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        from_date = self._parse_date(options['from_date'])
        to_date = self._parse_date(options['to_date'])
        if from_date > to_date:
            raise CommandError('--from must be <= --to')

        if options.get('account_id'):
            accounts = [get_broker_account_or_error(options['account_id'])]
        else:
            user = get_user_or_error(options['user_id']) if options.get('user_id') else User.objects.first()
            if not user:
                raise CommandError('Aucun utilisateur')
            accounts = [
                account for account in BrokerAccount.objects.filter(user=user, is_active=True)
                if (account.get_broker_type() or '').upper() == 'SAXO'
            ]

        if not accounts:
            raise CommandError('Aucun compte Saxo actif')

        dry_run = options['dry_run']
        for account in accounts:
            if (account.get_broker_type() or '').upper() != 'SAXO':
                self.stdout.write(self.style.WARNING(f'Skip account {account.id} (not SAXO)'))
                continue
            service = SaxoCostService.from_credentials(account.get_credentials_dict())
            rows = service.fetch_executed_costs(from_date, to_date)
            self.stdout.write(f'Account {account.id}: {len(rows)} report rows')
            if dry_run:
                for row in rows:
                    self.stdout.write(
                        f'  trade_id={row.trade_id} uic={row.uic} '
                        f'commission={row.commission} total={row.total_cost} {row.currency}'
                    )
                continue
            stats = service.persist_executed_costs(account.user, rows, source='report')
            self.stdout.write(self.style.SUCCESS(
                f"  created={stats['created']} updated={stats['updated']} unmatched={stats['unmatched']}"
            ))

    @staticmethod
    def _parse_date(value: str) -> date:
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError(f'Date invalide {value}, format attendu YYYY-MM-DD') from exc
