from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from apps.trading.models import BrokerAccount, Position, PortfolioSnapshot

class Command(BaseCommand):
    help = 'Prend un snapshot de la valeur du portefeuille pour tous les utilisateurs'

    def handle(self, *args, **options):
        self.stdout.write("Snapshotting portfolios...")
        
        users = User.objects.all()
        count = 0
        
        for user in users:
            try:
                # 1. Calculer les totaux
                broker_accounts = BrokerAccount.objects.filter(user=user, is_active=True)
                open_positions = Position.objects.filter(user=user, is_open=True)
                
                # Cash
                total_cash = sum(account.balance or 0 for account in broker_accounts)
                
                # Investi (somme des positions)
                total_invested = 0
                breakdown = {}
                
                # Initialiser breakdown pour chaque broker
                for account in broker_accounts:
                    broker_name = account.name or account.broker.name
                    breakdown[broker_name] = {
                        'cash': float(account.balance or 0),
                        'invested': 0.0,
                        'total': float(account.balance or 0)
                    }
                
                # Calculer la valeur des positions
                for pos in open_positions:
                    # Prix prioritaire: Yahoo > Current > Entry
                    price = pos.yahoo_current_price or pos.current_price or pos.entry_price or 0
                    if price and pos.quantity:
                        val = float(price) * float(pos.quantity)
                        total_invested += val
                        
                        # Ajouter au breakdown concerné
                        # On essaie de matcher le broker
                        if pos.broker:
                            # Trouver le compte correspondant à ce broker (tâtonnement simple)
                            # Idéalement pos.broker_account, mais on fait avec pos.broker
                            found = False
                            for acc in broker_accounts:
                                if acc.broker_id == pos.broker_id:
                                    broker_name = acc.name or acc.broker.name
                                    if broker_name in breakdown:
                                        breakdown[broker_name]['invested'] += val
                                        breakdown[broker_name]['total'] += val
                                        found = True
                                        break
                            
                            # Si pas trouvé de compte direct, on crée une entrée générique
                            if not found:
                                b_name = pos.broker.name
                                if b_name not in breakdown:
                                    breakdown[b_name] = {'cash': 0, 'invested': 0, 'total': 0}
                                breakdown[b_name]['invested'] += val
                                breakdown[b_name]['total'] += val
                
                total_value = float(total_cash) + total_invested
                
                # 2. Créer le snapshot
                PortfolioSnapshot.objects.create(
                    user=user,
                    total_value=total_value,
                    total_cash=total_cash,
                    total_invested=total_invested,
                    breakdown=breakdown
                )
                
                count += 1
                self.stdout.write(f"Snapshot created for {user.username}: {total_value}€")
                
            except Exception as e:
                self.stderr.write(f"Error for user {user.username}: {e}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {count} snapshots"))
