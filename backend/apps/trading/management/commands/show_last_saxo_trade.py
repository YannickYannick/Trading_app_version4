"""
Django management command to display the last SaxoBank trade.

Usage:
    python manage.py show_last_saxo_trade
    python manage.py show_last_saxo_trade --user-id 1
    python manage.py show_last_saxo_trade --account-id 2
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone

from apps.trading.models import Trade, BrokerAccount
from apps.trading.utils.user_utils import get_user_or_error


class Command(BaseCommand):
    help = 'Affiche le dernier trade SaxoBank'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID de l\'utilisateur (par défaut: premier utilisateur)'
        )
        parser.add_argument(
            '--account-id',
            type=int,
            help='ID du compte broker spécifique'
        )
    
    def handle(self, *args, **options):
        user_id = options.get('user_id')
        account_id = options.get('account_id')
        
        # Récupérer l'utilisateur
        if user_id:
            user = get_user_or_error(user_id)
        else:
            user = User.objects.first()
            if not user:
                raise CommandError("Aucun utilisateur trouvé dans la base de données")
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Recherche du dernier trade SaxoBank")
        self.stdout.write(f"{'='*60}\n")
        self.stdout.write(f"Utilisateur: {user.username} (ID: {user.id})\n")
        
        # Construire la requête pour les trades SaxoBank
        trades_query = Trade.objects.filter(
            user=user,
            broker__broker_type='SAXO'
        )
        
        # Si un account_id est spécifié, filtrer par compte
        if account_id:
            try:
                account = BrokerAccount.objects.get(id=account_id, user=user)
                if account.get_broker_type() != 'SAXO':
                    raise CommandError(f"Le compte {account_id} n'est pas un compte SaxoBank")
                trades_query = trades_query.filter(broker=account.broker)
                self.stdout.write(f"Compte broker: {account.name} (ID: {account.id})\n")
            except BrokerAccount.DoesNotExist:
                raise CommandError(f"Compte broker {account_id} introuvable")
        
        # Récupérer le dernier trade
        last_trade = trades_query.order_by('-executed_at').first()
        
        if not last_trade:
            self.stdout.write(
                self.style.WARNING("⚠️ Aucun trade SaxoBank trouvé")
            )
            return
        
        # Afficher les informations du trade
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"DERNIER TRADE SAXOBANK")
        self.stdout.write(f"{'='*60}\n")
        
        symbol = last_trade.all_asset.symbol if last_trade.all_asset else (
            last_trade.asset.symbol if last_trade.asset else 'Unknown'
        )
        
        self.stdout.write(f"ID: {last_trade.id}")
        self.stdout.write(f"Type: {last_trade.get_trade_type_display()}")
        self.stdout.write(f"Symbole: {symbol}")
        self.stdout.write(f"Quantité: {last_trade.quantity}")
        self.stdout.write(f"Prix: {last_trade.price}")
        self.stdout.write(f"Frais: {last_trade.fees}")
        self.stdout.write(f"Valeur totale: {last_trade.total_value}")
        self.stdout.write(f"Exécuté le: {last_trade.executed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculer le temps écoulé
        time_diff = timezone.now() - last_trade.executed_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days} jour(s) et {time_diff.seconds // 3600} heure(s)"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600} heure(s)"
        elif time_diff.seconds > 60:
            time_str = f"{time_diff.seconds // 60} minute(s)"
        else:
            time_str = f"{time_diff.seconds} seconde(s)"
        
        self.stdout.write(f"Il y a: {time_str}")
        
        if last_trade.broker_trade_id:
            self.stdout.write(f"ID broker: {last_trade.broker_trade_id}")
        
        if last_trade.broker:
            self.stdout.write(f"Broker: {last_trade.broker.name}")
        
        if last_trade.position:
            self.stdout.write(f"Position associée: {last_trade.position.id}")
        
        self.stdout.write(f"\nCréé le: {last_trade.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Modifié le: {last_trade.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Afficher les informations du AllAsset sous-jacent
        if last_trade.all_asset:
            all_asset = last_trade.all_asset
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"ALLASSET SOUS-JACENT")
            self.stdout.write(f"{'='*60}\n")
            
            self.stdout.write(f"ID: {all_asset.id}")
            self.stdout.write(f"Symbole: {all_asset.symbol}")
            self.stdout.write(f"Nom: {all_asset.name}")
            self.stdout.write(f"Plateforme: {all_asset.get_platform_display()}")
            self.stdout.write(f"Type d'actif: {all_asset.asset_type}")
            self.stdout.write(f"Marché: {all_asset.market}")
            self.stdout.write(f"Devise: {all_asset.currency}")
            
            if all_asset.exchange:
                self.stdout.write(f"Bourse: {all_asset.exchange}")
            
            self.stdout.write(f"Négociable: {'Oui' if all_asset.is_tradable else 'Non'}")
            
            # Informations Yahoo Finance
            self.stdout.write(f"\n--- Yahoo Finance ---")
            self.stdout.write(f"Symbole Yahoo: {all_asset.symbole_yahoo}")
            if all_asset.yahoo_validated_at:
                self.stdout.write(f"Validé le: {all_asset.yahoo_validated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if all_asset.yahoo_validation_method:
                self.stdout.write(f"Méthode de validation: {all_asset.yahoo_validation_method}")
            
            # Informations spécifiques Saxo
            if all_asset.platform == 'SAXO':
                self.stdout.write(f"\n--- Informations Saxo ---")
                if all_asset.saxo_uic:
                    self.stdout.write(f"UIC Saxo: {all_asset.saxo_uic}")
                if all_asset.saxo_exchange_id:
                    self.stdout.write(f"Exchange ID: {all_asset.saxo_exchange_id}")
                if all_asset.saxo_country_code:
                    self.stdout.write(f"Code pays: {all_asset.saxo_country_code}")
            
            # Historique des prix
            self.stdout.write(f"\n--- Historique des prix ---")
            if all_asset.has_price_history:
                history_count = all_asset.get_price_history_count()
                self.stdout.write(f"Nombre de jours d'historique: {history_count}")
                if all_asset.price_history_updated_at:
                    self.stdout.write(f"Dernière mise à jour: {all_asset.price_history_updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if all_asset.price_history_days > 0:
                    self.stdout.write(f"Jours stockés: {all_asset.price_history_days}")
                
                # Afficher les 5 dernières lignes sous forme de tableau
                dates = all_asset.get_price_history_dates()
                if dates:
                    self.stdout.write(f"\n{'='*120}")
                    self.stdout.write("5 DERNIÈRES LIGNES DE L'HISTORIQUE DES PRIX")
                    self.stdout.write(f"{'='*120}")
                    
                    # En-tête du tableau
                    header = f"{'Date':<12} | {'Open':>12} | {'High':>12} | {'Low':>12} | {'Close':>12} | {'Volume':>15} | {'Source':<10}"
                    separator = "-" * 120
                    self.stdout.write(header)
                    self.stdout.write(separator)
                    
                    # Afficher les 5 dernières dates
                    for date in dates[:5]:
                        price_data = all_asset.get_price_for_date(date)
                        if price_data:
                            open_price = price_data.get('open', 'N/A')
                            high_price = price_data.get('high', 'N/A')
                            low_price = price_data.get('low', 'N/A')
                            close_price = price_data.get('close', 'N/A')
                            volume = price_data.get('volume', 'N/A')
                            source = price_data.get('source', 'N/A')
                            
                            # Formater les prix (arrondir à 2 décimales si numérique)
                            def format_price(price):
                                if price == 'N/A':
                                    return 'N/A'.rjust(12)
                                try:
                                    return f"{float(price):.2f}".rjust(12)
                                except (ValueError, TypeError):
                                    return str(price).rjust(12)
                            
                            # Formater le volume
                            def format_volume(vol):
                                if vol == 'N/A':
                                    return 'N/A'.rjust(15)
                                try:
                                    vol_int = int(float(vol))
                                    if vol_int >= 1_000_000:
                                        return f"{vol_int / 1_000_000:.2f}M".rjust(15)
                                    elif vol_int >= 1_000:
                                        return f"{vol_int / 1_000:.2f}K".rjust(15)
                                    else:
                                        return str(vol_int).rjust(15)
                                except (ValueError, TypeError):
                                    return str(vol).rjust(15)
                            
                            row = (
                                f"{date:<12} | "
                                f"{format_price(open_price)} | "
                                f"{format_price(high_price)} | "
                                f"{format_price(low_price)} | "
                                f"{format_price(close_price)} | "
                                f"{format_volume(volume)} | "
                                f"{source:<10}"
                            )
                            self.stdout.write(row)
                    
                    self.stdout.write(f"{'='*120}")
            else:
                self.stdout.write("Aucun historique de prix disponible")
            
            self.stdout.write(f"\nCréé le: {all_asset.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"Dernière mise à jour: {all_asset.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write("⚠️ Aucun AllAsset associé à ce trade")
        
        self.stdout.write(f"\n{'='*60}")

