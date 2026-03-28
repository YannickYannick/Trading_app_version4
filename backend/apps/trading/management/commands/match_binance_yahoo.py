from django.core.management.base import BaseCommand
from apps.trading.models import AllAssets
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from django.db.models import Q

class Command(BaseCommand):
    help = 'Tente de faire correspondre les actifs Binance avec les symboles Yahoo Finance (USD/EUR)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Démarrage de la réconciliation Binance -> Yahoo..."))

        # Récupérer les assets Binance non validés (ou tous si besoin de forcer)
        # On exclut ceux déjà validés manuellement ou trouvés
        assets = AllAssets.objects.filter(platform='BINANCE').filter(
            Q(symbole_yahoo='Not_searched') | Q(symbole_yahoo='not_found')
        )
        
        # Si vous voulez tout forcer, commentez le fltre Q ci-dessus.
        # assets = AllAssets.objects.filter(platform='BINANCE')

        total_assets = assets.count()
        self.stdout.write(f"📋 {total_assets} actifs à analyser.")

        if total_assets == 0:
            self.stdout.write(self.style.SUCCESS("✅ Aucun actif à traiter."))
            return

        def process_asset(asset):
            symbol = asset.symbol
            # On retire USDT, BUSD si présent dans le nom (Binance stocke souvent 'BTCUSDT' comme symbole brut ?)
            # AllAssets.symbol est généralement le ticker de base 'BTC'.
            # Vérifions : sur Binance 'BTC' est l'asset, 'BTCUSDT' est la paire.
            # Le modèle AllAssets stocke 'BTC' normalement si c'est un asset, ou la paire ?
            # D'après le script user : "process_asset(symbol_base)" donc on suppose qu'on a la base.
            
            # 1. Tester SYMBOL-USD (Y8)
            y8_ticker = f"{symbol}-USD"
            if self.check_yahoo_ticker(y8_ticker):
                return asset, y8_ticker, 'Y8'

            # 2. Tester SYMBOL-EUR (Y9)
            y9_ticker = f"{symbol}-EUR"
            if self.check_yahoo_ticker(y9_ticker):
                return asset, y9_ticker, 'Y9'
            
            return asset, None, None

        updated_count = 0
        MAX_WORKERS = 20
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_asset = {executor.submit(process_asset, asset): asset for asset in assets}
            
            for i, future in enumerate(as_completed(future_to_asset)):
                asset = future_to_asset[future]
                try:
                    processed_asset, valid_ticker, method = future.result()
                    
                    if valid_ticker:
                        processed_asset.set_yahoo_symbol(valid_ticker, method=method)
                        self.stdout.write(self.style.SUCCESS(f"✅ Trouvé : {processed_asset.symbol} -> {valid_ticker} ({method})"))
                        updated_count += 1
                    else:
                        # Marquer comme non trouvé pour ne pas re-scanner à chaque fois
                        processed_asset.symbole_yahoo = 'not_found'
                        processed_asset.save(update_fields=['symbole_yahoo'])
                        # self.stdout.write(self.style.WARNING(f"❌ Non trouvé : {processed_asset.symbol}"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erreur pour {asset.symbol}: {e}"))
                
                if i % 10 == 0:
                     self.stdout.write(f"⏳ Progression : {i}/{total_assets}...", ending='\r')

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Terminé ! {updated_count}/{total_assets} actifs mis à jour."))

    def check_yahoo_ticker(self, ticker):
        """Vérifie si un ticker existe sur Yahoo Finance et a un prix récent."""
        try:
            t = yf.Ticker(ticker)
            # fast_info est plus rapide et ne télécharge pas tout l'historique
            price = t.fast_info.last_price
            return price is not None and price > 0
        except Exception:
            return False
