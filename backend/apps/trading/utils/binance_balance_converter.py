"""
Utilitaire pour convertir les balances Binance en EUR.

Binance retourne les balances en différentes devises crypto (BTC, ETH, USDT, etc.)
mais pas directement en EUR. Cette fonction convertit toutes les balances en EUR.
"""
from decimal import Decimal
from typing import Dict, Optional
import logging

logger = logging.getLogger('trading.utils.binance_converter')


def convert_binance_balances_to_eur(
    balances: Dict[str, Decimal],
    broker_instance=None
) -> Dict[str, Decimal]:
    """
    Convertit les balances Binance en EUR.
    
    Args:
        balances: Dict des balances de Binance {asset: Decimal, ...}
        broker_instance: Instance du broker Binance pour récupérer les prix (optionnel)
        
    Returns:
        Dict avec 'EUR': total_eur, et toutes les balances converties
    """
    if not balances:
        return {'EUR': Decimal('0')}
    
    # Nettoyer les balances (enlever les clés _free, _locked, etc.)
    clean_balances = {}
    for key, value in balances.items():
        if not key.endswith('_free') and not key.endswith('_locked') and not key.endswith('_margin_available') and not key.endswith('_total'):
            # Convertir en Decimal si nécessaire
            try:
                decimal_value = Decimal(str(value)) if not isinstance(value, Decimal) else value
                if decimal_value > 0:
                    clean_balances[key] = decimal_value
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not convert balance value for {key}: {value} (error: {e})")
    
    if not clean_balances:
        return {'EUR': Decimal('0')}
    
    total_eur = Decimal('0')
    converted_balances = {}
    
    # Ordre de priorité pour la conversion EUR
    # On essaie d'abord les paires directes EUR, puis USDT, puis BTC/ETH
    conversion_order = [
        ('EUR', None),  # EUR direct
        ('USDT', 'EURT'),  # USDT -> EURT (Tether EUR)
        ('USDT', 'USDTEUR'),  # USDT -> USDT/EUR
        ('BTC', 'BTCEUR'),  # BTC -> BTC/EUR
        ('ETH', 'ETHEUR'),  # ETH -> ETH/EUR
        ('BNB', 'BNBEUR'),  # BNB -> BNB/EUR
    ]
    
    # Taux de conversion par défaut (si pas de broker_instance)
    # Ces valeurs sont des approximations et devraient être récupérées via l'API
    default_rates = {
        'EUR': Decimal('1'),
        'EURT': Decimal('1'),  # Tether EUR ≈ 1 EUR
        'USDTEUR': Decimal('0.92'),  # Approximation USDT ≈ 0.92 EUR
        'USDC': Decimal('0.92'),  # USDC ≈ 1 USD ≈ 0.92 EUR (approximation)
        'BUSD': Decimal('0.92'),  # BUSD ≈ 1 USD ≈ 0.92 EUR (approximation)
        'DAI': Decimal('0.92'),  # DAI ≈ 1 USD ≈ 0.92 EUR (approximation)
        'BTCEUR': Decimal('95000'),  # Approximation BTC
        'ETHEUR': Decimal('3500'),  # Approximation ETH
        'BNBEUR': Decimal('600'),  # Approximation BNB
    }
    
    # Liste des stablecoins qui valent environ 1 USD/EUR
    stablecoins = {'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'EURT'}
    
    logger.info(f"Starting conversion of {len(clean_balances)} assets: {list(clean_balances.keys())}")
    
    for asset, balance in clean_balances.items():
        asset_upper = asset.upper()
        converted_value = Decimal('0')
        conversion_method = None
        
        # Cas 1: Asset est déjà EUR
        if asset_upper == 'EUR':
            converted_value = balance
            converted_balances[asset] = balance
            conversion_method = 'EUR direct'
            logger.info(f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method})")
        
        # Cas 2: Essayer de trouver une paire de trading EUR
        elif broker_instance and hasattr(broker_instance, 'get_asset_price'):
            # Essayer les paires directes (assetEUR)
            eur_pair = f"{asset_upper}EUR"
            try:
                price = broker_instance.get_asset_price(eur_pair)
                if price and price > 0:
                    converted_value = balance * price
                    converted_balances[asset] = balance
                    conversion_method = f'API direct {eur_pair}'
                    logger.info(f"[{asset_upper}] {balance} → {converted_value} EUR via {eur_pair} = {price}")
            except Exception as e:
                logger.debug(f"Could not get price for {eur_pair}: {e}")
            
            # Si pas de paire directe, essayer via USDT (assetUSDT puis USDTEUR)
            if converted_value == 0:
                try:
                    usdt_pair = f"{asset_upper}USDT"
                    usdt_price = broker_instance.get_asset_price(usdt_pair)
                    if usdt_price and usdt_price > 0:
                        # Ensuite convertir USDT en EUR
                        usdt_eur_pair = 'USDTEUR'
                        usdt_eur_price = broker_instance.get_asset_price(usdt_eur_pair)
                        if not usdt_eur_price or usdt_eur_price <= 0:
                            usdt_eur_price = default_rates.get('USDTEUR', Decimal('0.92'))
                            logger.debug(f"Using default USDTEUR rate: {usdt_eur_price}")
                        
                        converted_value = balance * usdt_price * usdt_eur_price
                        converted_balances[asset] = balance
                        conversion_method = f'API via USDT ({usdt_pair}={usdt_price}, {usdt_eur_pair}={usdt_eur_price})'
                        logger.info(f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method})")
                except Exception as e:
                    logger.debug(f"Could not convert {asset_upper} via USDT: {e}")
            
            # Si toujours pas converti, essayer les taux par défaut pour les paires courantes
            if converted_value == 0:
                # Chercher dans les paires EUR directes
                eur_pair_key = f"{asset_upper}EUR"
                if eur_pair_key in default_rates:
                    rate = default_rates[eur_pair_key]
                    converted_value = balance * rate
                    converted_balances[asset] = balance
                    conversion_method = f'Default rate {eur_pair_key}'
                    logger.warning(f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method}: {rate})")
                # Sinon chercher dans conversion_order
                elif asset_upper in [base for base, _ in conversion_order]:
                    for base_asset, pair in conversion_order:
                        if asset_upper == base_asset and pair in default_rates:
                            rate = default_rates[pair]
                            converted_value = balance * rate
                            converted_balances[asset] = balance
                            conversion_method = f'Default rate {pair}'
                            logger.warning(f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method}: {rate})")
                            break
            
            # Dernier recours: Essayer via USDT avec taux par défaut ou utiliser taux stablecoin
            if converted_value == 0:
                # Vérifier si c'est un stablecoin connu
                if asset_upper in stablecoins:
                    # Les stablecoins valent environ 1 USD ≈ 0.92 EUR
                    stablecoin_rate = default_rates.get(asset_upper, default_rates.get('USDTEUR', Decimal('0.92')))
                    converted_value = balance * stablecoin_rate
                    converted_balances[asset] = balance
                    conversion_method = f'Stablecoin default rate ({asset_upper} ≈ 1 USD)'
                    logger.warning(
                        f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method}: {stablecoin_rate})"
                    )
                # Si ce n'est pas un stablecoin, logger un warning
                else:
                    logger.warning(
                        f"[{asset_upper}] {balance} → 0 EUR (could not convert: no API price available and no default rate). "
                        f"Asset value not included in total. Consider adding a default rate for this asset."
                    )
        
        else:
            # Pas de broker_instance, utiliser les taux par défaut
            # Chercher une paire disponible
            for base_asset, pair in conversion_order:
                if asset_upper == base_asset:
                    if pair and pair in default_rates:
                        rate = default_rates[pair]
                        converted_value = balance * rate
                        converted_balances[asset] = balance
                        conversion_method = f'Default rate {pair} (no broker instance)'
                        logger.info(f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method}: {rate})")
                        break
            
            # Si toujours pas trouvé, essayer directement le nom de l'asset comme clé (pour les paires EUR directes)
            if converted_value == 0:
                eur_pair_key = f"{asset_upper}EUR"
                if eur_pair_key in default_rates:
                    rate = default_rates[eur_pair_key]
                    converted_value = balance * rate
                    converted_balances[asset] = balance
                    conversion_method = f'Default rate {eur_pair_key} (no broker instance)'
                    logger.info(f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method}: {rate})")
                # Vérifier si c'est un stablecoin
                elif asset_upper in stablecoins:
                    stablecoin_rate = default_rates.get(asset_upper, default_rates.get('USDTEUR', Decimal('0.92')))
                    converted_value = balance * stablecoin_rate
                    converted_balances[asset] = balance
                    conversion_method = f'Stablecoin default rate (no broker instance, {asset_upper} ≈ 1 USD)'
                    logger.info(f"[{asset_upper}] {balance} → {converted_value} EUR ({conversion_method}: {stablecoin_rate})")
                else:
                    logger.warning(
                        f"[{asset_upper}] {balance} → 0 EUR (could not convert: no broker instance and no default rate). "
                        f"Asset value not included in total."
                    )
        
        total_eur += converted_value
    
    logger.info(f"Conversion complete: total EUR = {total_eur}")
    
    # Ajouter le total EUR
    converted_balances['EUR'] = total_eur
    
    return converted_balances


def get_binance_eur_balance(
    balances: Dict[str, Decimal],
    broker_instance=None
) -> Decimal:
    """
    Récupère uniquement le solde EUR total depuis les balances Binance.
    
    Args:
        balances: Dict des balances de Binance
        broker_instance: Instance du broker Binance pour récupérer les prix
        
    Returns:
        Solde total en EUR
    """
    converted = convert_binance_balances_to_eur(balances, broker_instance)
    eur = converted.get('EUR', Decimal('0'))
    if eur == 0 and balances:
        # Log léger pour diagnostiquer les "0€" en prod sans exposer de valeurs.
        clean_keys = [
            k
            for k in balances.keys()
            if not k.endswith('_free')
            and not k.endswith('_locked')
            and not k.endswith('_margin_available')
            and not k.endswith('_total')
        ]
        logger.warning(
            f"Binance EUR balance is 0 after conversion: assets_count={len(clean_keys)} "
            f"sample_assets={clean_keys[:25]} has_broker_instance={bool(broker_instance)}"
        )
        logger.warning(
            "Binance EUR balance is 0 after conversion",
            extra={
                "binance": {
                    "assets_count": len(clean_keys),
                    "assets": clean_keys[:25],  # échantillon
                    "has_broker_instance": bool(broker_instance),
                }
            },
        )
    return eur

