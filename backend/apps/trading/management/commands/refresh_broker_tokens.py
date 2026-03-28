"""
Commande Django pour rafraîchir automatiquement les tokens des brokers.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from apps.trading.models import BrokerAccount
from apps.trading.services.broker_service import BrokerService
from apps.trading.utils.token_utils import parse_iso_datetime
from apps.trading.constants import DEFAULT_TOKEN_REFRESH_MINUTES_BEFORE
import logging
import os
from pathlib import Path

logger = logging.getLogger('trading.management.refresh_tokens')

# Chemin du fichier de log (compatible local et production)
if os.path.exists('/home/lebaffc1/logs'):
    LOG_FILE = '/home/lebaffc1/logs/cron_saxo_tokens.log'
else:
    # Environnement local
    LOG_FILE = Path(__file__).resolve().parent.parent.parent.parent.parent / 'logs' / 'cron_saxo_tokens.log'


class Command(BaseCommand):
    help = 'Rafraîchit les tokens des brokers qui expirent bientôt'
    
    def log_and_print(self, message, style=None):
        """Écrit dans stdout ET dans le fichier de log"""
        # Afficher dans la console
        if style:
            self.stdout.write(style(message))
        else:
            self.stdout.write(message)
        
        # Écrire dans le fichier de log
        try:
            # Créer le dossier logs s'il n'existe pas
            log_dir = os.path.dirname(LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Ajouter au fichier avec timestamp
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                # Retirer les codes couleur ANSI pour le fichier
                clean_message = message
                f.write(f"[{timestamp}] {clean_message}\n")
        except Exception as e:
            # Ne pas crasher si on ne peut pas écrire dans le log
            self.stdout.write(f"⚠️ Impossible d'écrire dans le log: {e}")
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes-before',
            type=int,
            default=DEFAULT_TOKEN_REFRESH_MINUTES_BEFORE,
            help=f'Rafraîchir les tokens expirant dans X minutes (défaut: {DEFAULT_TOKEN_REFRESH_MINUTES_BEFORE})'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forcer le refresh de tous les tokens valides (ignorer la date d\'expiration)'
        )
        parser.add_argument(
            '--broker-type',
            type=str,
            help='Limiter au type de broker spécifié (SAXO, BINANCE, etc.)'
        )
        parser.add_argument(
            '--account-id',
            type=int,
            help='Rafraîchir un compte spécifique par ID'
        )
    
    def handle(self, *args, **options):
        minutes_before = options['minutes_before']
        force = options['force']
        broker_type_filter = options.get('broker_type')
        account_id = options.get('account_id')
        
        # Créer un seuil d'expiration
        threshold = timezone.now() + timedelta(minutes=minutes_before)
        
        self.log_and_print(
            f'🔄 Recherche des tokens à rafraîchir (expiration < {threshold})...',
            self.style.SUCCESS
        )
        
        # Construire la requête
        accounts_query = BrokerAccount.objects.filter(
            is_active=True,
            broker_type='SAXO'  # Pour l'instant, seul Saxo utilise OAuth2
        )
        
        # Filtrer par type de broker si spécifié
        if broker_type_filter:
            accounts_query = accounts_query.filter(broker_type=broker_type_filter)
        
        # Filtrer par ID de compte si spécifié
        if account_id:
            accounts_query = accounts_query.filter(id=account_id)
        
        # Filtrer par expiration si pas force
        if not force:
            # Tokens avec refresh_token et expirant bientôt
            accounts_query = accounts_query.filter(
                saxo_refresh_token__isnull=False
            ).exclude(saxo_refresh_token='')
            
            # Si on a une date d'expiration, filtrer
            accounts_to_refresh = []
            for account in accounts_query:
                # Si pas de date d'expiration, considérer comme à refresh
                if not account.saxo_token_expires_at:
                    accounts_to_refresh.append(account)
                    continue
                
                # Si expire avant le seuil, ajouter
                if account.saxo_token_expires_at <= threshold:
                    accounts_to_refresh.append(account)
        else:
            # Force: tous les comptes avec refresh_token
            accounts_to_refresh = list(
                accounts_query.filter(
                    saxo_refresh_token__isnull=False
                ).exclude(saxo_refresh_token='')
            )
        
        if not accounts_to_refresh:
            self.log_and_print(
                'Aucun token à rafraîchir.',
                self.style.WARNING
            )
            return
        
        self.log_and_print(
            f'📋 {len(accounts_to_refresh)} compte(s) trouvé(s)'
        )
        
        refreshed = 0
        failed = 0
        skipped = 0
        
        # Utiliser le premier utilisateur admin ou créer un utilisateur système
        try:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
        except Exception:
            user = None
        
        if not user:
            self.stdout.write(
                self.style.ERROR('❌ Aucun utilisateur trouvé pour exécuter le service.')
            )
            return
        
        for account in accounts_to_refresh:
            try:
                self.stdout.write(
                    f'  🔄 Rafraîchissement du token pour {account.name} (ID: {account.id})...'
                )
                
                service = BrokerService(user)
                broker = service.get_broker_instance(account, use_cache=False)
                
                # Rafraîchir le token
                success = broker._refresh_token()
                
                if success:
                    # Sauvegarder les nouveaux tokens
                    account.saxo_access_token = broker.access_token
                    if broker.refresh_token:
                        account.saxo_refresh_token = broker.refresh_token
                    
                    # Parser et sauvegarder la date d'expiration
                    if broker.token_expires_at:
                        try:
                            expires_at = parse_iso_datetime(broker.token_expires_at)
                            if expires_at:
                                # S'assurer que la date est timezone-aware
                                if expires_at.tzinfo is None:
                                    expires_at = timezone.make_aware(expires_at)
                                account.saxo_token_expires_at = expires_at
                        except Exception as e:
                            logger.warning(
                                f"Impossible de parser token_expires_at pour "
                                f"account {account.id}: {e}"
                            )
                    
                    account.save(
                        update_fields=[
                            'saxo_access_token',
                            'saxo_refresh_token',
                            'saxo_token_expires_at'
                        ]
                    )
                    
                    refreshed += 1
                    expires_str = (
                        account.saxo_token_expires_at.strftime('%Y-%m-%d %H:%M:%S')
                        if account.saxo_token_expires_at
                        else 'N/A'
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'    ✅ Token rafraîchi (expire: {expires_str})'
                        )
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR('    ❌ Échec du rafraîchissement')
                    )
                    
            except Exception as e:
                failed += 1
                error_msg = str(e)
                logger.error(
                    f"Erreur lors du rafraîchissement du token pour "
                    f"account {account.id}: {e}",
                    exc_info=True
                )
                self.stdout.write(
                    self.style.ERROR(f'    ❌ Erreur: {error_msg}')
                )
        
        # Résumé
        self.log_and_print('')
        self.log_and_print('📊 Résumé:', self.style.SUCCESS)
        self.log_and_print(f'  ✅ Rafraîchis: {refreshed}')
        self.log_and_print(f'  ❌ Échecs: {failed}')
        self.log_and_print(f'  ⏭️  Ignorés: {skipped}')
        
        if refreshed > 0:
            self.log_and_print(
                f'\n✅ {refreshed} token(s) rafraîchi(s) avec succès!',
                self.style.SUCCESS
            )

