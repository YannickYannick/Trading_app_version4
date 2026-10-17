"""
Exécute les stratégies actives + automatisées selon check_frequency.

Usage (local) :
  python manage.py execute_automated_strategies
  python manage.py execute_automated_strategies --dry-run
  python manage.py execute_automated_strategies --force
  python manage.py execute_automated_strategies --ids 1,2,3

Cron HostArmada (toutes les 5 min) :
  */5 * * * * cd /path/to/backend && python manage.py execute_automated_strategies >> /path/to/logs/cron_strategies.log 2>&1
"""
from django.core.management.base import BaseCommand

from apps.trading.services.strategy_executor import StrategyExecutor


class Command(BaseCommand):
    help = 'Exécute les stratégies is_active + is_automated dues (check_frequency)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Calcule les signaux sans passer d\'ordres broker',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ignore check_frequency (exécute toutes les stratégies auto actives)',
        )
        parser.add_argument(
            '--ids',
            type=str,
            default='',
            help='Liste d\'IDs de stratégies séparés par des virgules',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        ids_raw = (options.get('ids') or '').strip()
        strategy_ids = None
        if ids_raw:
            strategy_ids = [int(x) for x in ids_raw.split(',') if x.strip().isdigit()]

        self.stdout.write(
            self.style.NOTICE(
                f'Exécution auto (dry_run={dry_run}, force={force}, ids={strategy_ids or "all"})…'
            )
        )

        summary = StrategyExecutor().run_due_strategies(
            force=force,
            dry_run=dry_run,
            strategy_ids=strategy_ids,
        )

        for row in summary['results']:
            sid = row.get('strategy_id')
            name = row.get('name')
            status = row.get('status')
            if status == 'skipped':
                self.stdout.write(f'  skip  #{sid} {name} ({row.get("reason")})')
            elif status == 'success':
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ok    #{sid} {name} signal={row.get("signal")} qty={row.get("signal_quantity")}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'  fail  #{sid} {name} error={row.get("error")}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Terminé : ran={summary["ran"]} skipped={summary["skipped"]} dry_run={summary["dry_run"]}'
            )
        )
