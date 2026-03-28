"""
Commande Django pour générer les rapports IA quotidiens.

Usage:
    python manage.py generate_daily_ai_report
    python manage.py generate_daily_ai_report --dry-run
    python manage.py generate_daily_ai_report --user=username
"""
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from apps.ai_assistant.services.trading_analysis_service import TradingAnalysisService
from apps.trading.models import Strategy

logger = logging.getLogger('ai_assistant')


class Command(BaseCommand):
    help = 'Génère les rapports IA quotidiens pour tous les utilisateurs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username spécifique à analyser (optionnel)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait fait sans exécuter',
        )
    
    def handle(self, *args, **options):
        """Exécute la commande."""
        dry_run = options.get('dry_run', False)
        username = options.get('user')
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'[DRY RUN] ' if dry_run else ''}Génération des rapports IA quotidiens"
            )
        )
        self.stdout.write(f"Heure: {timezone.now()}\n")
        
        # Déterminer les utilisateurs à analyser
        if username:
            try:
                users = [User.objects.get(username=username)]
                self.stdout.write(f"Analyse pour l'utilisateur: {username}\n")
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Utilisateur '{username}' introuvable")
                )
                return
        else:
            # Tous les utilisateurs avec au moins une stratégie active
            users = User.objects.filter(
                strategies__is_active=True
            ).distinct()
            self.stdout.write(f"Analyse pour {users.count()} utilisateur(s)\n")
        
        # Initialiser le service d'analyse
        analysis_service = TradingAnalysisService()
        
        # Compteurs
        total_analyses = 0
        total_success = 0
        total_errors = 0
        
        # Pour chaque utilisateur
        for user in users:
            self.stdout.write(f"\n{'─' * 60}")
            self.stdout.write(f"Utilisateur: {user.username}")
            
            # 1. Analyse de portefeuille
            self.stdout.write("  → Analyse de portefeuille...")
            if not dry_run:
                try:
                    analysis = analysis_service.analyze_portfolio(user)
                    analysis.is_daily_report = True
                    analysis.save(update_fields=['is_daily_report'])
                    
                    if analysis.status == 'COMPLETED':
                        self.stdout.write(self.style.SUCCESS("    ✓ Succès"))
                        total_success += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"    ✗ Échec: {analysis.error_message}"))
                        total_errors += 1
                    
                    total_analyses += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ✗ Erreur: {str(e)}"))
                    logger.error(f"Erreur lors de l'analyse du portefeuille pour {user.username}: {e}")
                    total_errors += 1
            else:
                self.stdout.write("    [Simulé]")
            
            # 2. Analyses de stratégies individuelles
            active_strategies = Strategy.objects.filter(user=user, is_active=True)
            self.stdout.write(f"  → {active_strategies.count()} stratégie(s) active(s)")
            
            for strategy in active_strategies:
                self.stdout.write(f"    - {strategy.name}...")
                if not dry_run:
                    try:
                        analysis = analysis_service.analyze_strategy(strategy, user)
                        analysis.is_daily_report = True
                        analysis.save(update_fields=['is_daily_report'])
                        
                        if analysis.status == 'COMPLETED':
                            self.stdout.write(self.style.SUCCESS("      ✓ Succès"))
                            total_success += 1
                        else:
                            self.stdout.write(self.style.ERROR(f"      ✗ Échec: {analysis.error_message}"))
                            total_errors += 1
                        
                        total_analyses += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"      ✗ Erreur: {str(e)}"))
                        logger.error(f"Erreur lors de l'analyse de la stratégie {strategy.name}: {e}")
                        total_errors += 1
                else:
                    self.stdout.write("      [Simulé]")
        
        # Résumé
        self.stdout.write(f"\n{'═' * 60}")
        self.stdout.write(self.style.SUCCESS("\nRÉSUMÉ:"))
        self.stdout.write(f"  Total d'analyses: {total_analyses}")
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"  Succès: {total_success}"))
            if total_errors > 0:
                self.stdout.write(self.style.ERROR(f"  Erreurs: {total_errors}"))
        else:
            self.stdout.write("  Mode: DRY RUN (aucune analyse créée)")
        
        self.stdout.write(f"\n{'═' * 60}\n")
        
        if not dry_run and total_errors == 0:
            self.stdout.write(
                self.style.SUCCESS("✓ Tous les rapports ont été générés avec succès!")
            )
        elif not dry_run and total_errors > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠ Terminé avec {total_errors} erreur(s)")
            )
