"""
Service de validation Yahoo Finance pour les assets.

Ce module implémente la logique de validation en cascade (Y4 → Y3 → Y0)
pour trouver le symbole Yahoo Finance correspondant à chaque asset.
"""

import re
import logging
import requests
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from ..utils.yahoo_config import (
    MIC_TO_YAHOO_SUFFIX,
    DEFAULT_PRICE_TOLERANCE_PERCENT,
    REQUEST_TIMEOUT,
    DEFAULT_MAX_WORKERS,
    CACHE_SIZE,
    PROGRESS_INTERVAL,
    ValidationStatus,
    clean_company_name,
    get_yahoo_suffix,
)

logger = logging.getLogger('trading_app.yahoo_validator')

# ==============================================================================
# 🔧 SESSION HTTP GLOBALE
# ==============================================================================

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})


# ==============================================================================
# 📊 DATA CLASSES
# ==============================================================================

@dataclass
class ValidationResult:
    """Résultat de la validation d'un asset."""
    yahoo_symbol: str
    status: str
    method: str = ''
    yahoo_price: Optional[float] = None
    broker_price: Optional[float] = None
    error_message: str = ''


@dataclass 
class ValidationStats:
    """Statistiques de validation."""
    total: int = 0
    validated_y4: int = 0
    validated_y3: int = 0
    validated_y0: int = 0
    not_found: int = 0
    errors: int = 0
    skipped: int = 0
    
    @property
    def validated_total(self) -> int:
        return self.validated_y4 + self.validated_y3 + self.validated_y0
    
    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.validated_total / self.total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'validated_y4': self.validated_y4,
            'validated_y3': self.validated_y3,
            'validated_y0': self.validated_y0,
            'validated_total': self.validated_total,
            'not_found': self.not_found,
            'errors': self.errors,
            'skipped': self.skipped,
            'success_rate': self.success_rate,
        }


# ==============================================================================
# 🧠 FONCTIONS CACHÉES (YAHOO API)
# ==============================================================================

@lru_cache(maxsize=CACHE_SIZE)
def get_yahoo_price(ticker: str) -> Optional[float]:
    """
    Récupère le prix d'un ticker Yahoo Finance (avec cache LRU).
    
    Args:
        ticker: Symbole Yahoo (ex: 'AAPL', 'MC.PA')
        
    Returns:
        Prix ou None si non trouvé
    """
    if not ticker:
        return None
    
    try:
        t = yf.Ticker(ticker)
        price = t.fast_info.last_price
        return float(price) if price else None
    except Exception as e:
        logger.debug(f"Yahoo price error for {ticker}: {e}")
        return None


@lru_cache(maxsize=CACHE_SIZE)
def yahoo_search_by_name(query: str) -> Optional[str]:
    """
    Recherche un ticker Yahoo par nom d'entreprise (avec cache LRU).
    
    Args:
        query: Nom de l'entreprise à rechercher
        
    Returns:
        Symbole Yahoo ou None si non trouvé
    """
    if not query or len(query) < 2:
        return None
    
    try:
        response = _session.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={
                "q": query,
                "quotesCount": 5,
                "newsCount": 0,
                "enableFuzzyQuery": True,
            },
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            quotes = data.get("quotes", [])
            
            if quotes:
                # Prendre le premier résultat de type equity
                for quote in quotes:
                    quote_type = quote.get("quoteType", "").upper()
                    if quote_type in ["EQUITY", "ETF"]:
                        return quote.get("symbol")
                
                # Si aucun equity, prendre le premier
                return quotes[0].get("symbol")
                
    except requests.exceptions.Timeout:
        logger.warning(f"Yahoo search timeout for: {query}")
    except Exception as e:
        logger.debug(f"Yahoo search error for {query}: {e}")
    
    return None


# ==============================================================================
# 💰 RÉCUPÉRATION PRIX BROKER
# ==============================================================================

def get_saxo_price(
    access_token: str, 
    uic: int, 
    asset_type: str = "Stock",
    # ✅ MIGRATION: URL changée de SIM vers LIVE
    base_url: str = "https://gateway.saxobank.com/openapi"
) -> Optional[float]:
    """
    Récupère le prix actuel depuis l'API Saxo Bank.
    
    Args:
        access_token: Token d'accès Saxo OAuth2
        uic: Unique Instrument Code Saxo
        asset_type: Type d'actif (Stock, Etf, etc.)
        base_url: URL de base de l'API (sim ou live)
        
    Returns:
        Prix ou None si non disponible
    """
    if not access_token or not uic:
        return None
    
    # Détecter l'environnement depuis l'URL pour logging
    environment = "LIVE" if "/sim/" not in base_url else "SIM"
    token_preview = access_token[:20] + "..." if access_token else "None"
    
    logger.debug(f"🔍 Getting Saxo price for UIC {uic} ({asset_type}) - Environment: {environment}, URL: {base_url}, Token: {token_preview}")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        # Utiliser FieldGroups pour obtenir les champs de prix complets
        # Utiliser PriceInfo et Quote pour avoir toutes les options
        params = {
            "Uic": uic,
            "AssetType": asset_type,
            "FieldGroups": "PriceInfo,Quote"  # Inclure PriceInfo pour LastTraded, Bid, Ask
        }
        
        full_url = f"{base_url}/trade/v1/infoprices"
        logger.debug(f"📡 Request URL: {full_url} with params: {params}")
        
        response = requests.get(
            full_url,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        logger.debug(f"📥 Response status: {response.status_code} for UIC {uic}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Log pour débogage
            logger.debug(f"Saxo API response for UIC {uic}: {str(data)[:500]}")
            
            # ✅ CORRECTION: L'API LIVE retourne directement {"Quote": {...}} avec Mid, Bid, Ask
            # L'API peut retourner soit {"Data": [...]} soit directement l'objet avec Quote
            
            quote = None
            price_info = None
            
            # Vérifier si c'est un tableau Data
            if "Data" in data:
                data_items = data.get("Data", [])
                if data_items:
                    first_item = data_items[0]
                    quote = first_item.get("Quote", {})
                    price_info = first_item.get("PriceInfo", {})
            
            # Sinon, structure directe (format observé en LIVE et parfois en SIM)
            if not quote:
                quote = data.get("Quote", {})
                price_info = data.get("PriceInfo", {})
            
            if not quote:
                logger.warning(f"No Quote in response for UIC {uic}, response keys: {list(data.keys())}")
                return None
            
            # Vérifier si l'accès au prix est bloqué
            price_type_ask = quote.get("PriceTypeAsk", "")
            price_type_bid = quote.get("PriceTypeBid", "")
            if price_type_ask == "NoAccess" and price_type_bid == "NoAccess":
                logger.warning(
                    f"❌ {environment} MODE: Price access denied for UIC {uic} "
                    f"(PriceTypeAsk={price_type_ask}, PriceTypeBid={price_type_bid}). "
                    f"⚠️ Possible causes: "
                    f"{'1) Token SIM used with LIVE URL' if environment == 'LIVE' else '1) Token LIVE used with SIM URL'}, "
                    f"2) Market Data subscription not activated, "
                    f"3) Instrument not available for this account. "
                    f"URL used: {base_url}"
                )
                # En LIVE, NoAccess signifie généralement que les permissions Market Data ne sont pas activées
                # ou que l'instrument n'est pas disponible
                # Ou que le token n'est pas compatible avec l'environnement (SIM token avec LIVE URL)
                return None
            
            # ✅ PRIORITÉ: Mid > Bid > Ask (format standard de l'API LIVE)
            # En LIVE, ces champs sont directement disponibles dans Quote
            price = quote.get("Mid") or quote.get("Bid") or quote.get("Ask")
            
            if price:
                logger.info(f"✅ {environment} MODE: Saxo price found for UIC {uic}: {price} (Mid={quote.get('Mid')}, Bid={quote.get('Bid')}, Ask={quote.get('Ask')})")
                return float(price)
            
            # Format alternatif: Amount (pour certains types d'instruments)
            if "Amount" in quote:
                amount = quote.get("Amount")
                # Amount peut être un montant nominal (ex: 10000 pour EURUSD)
                # Ne pas utiliser Amount comme prix sauf indication contraire
                if amount and amount > 0 and amount != 10000:  # 10000 est souvent un nominal, pas un prix
                    logger.debug(f"Using Amount field for UIC {uic}: {amount}")
                    return float(amount)
            
            # Format PriceInfo si disponible
            if not price and price_info:
                price = price_info.get("LastTraded") or price_info.get("Bid") or price_info.get("Ask")
                if price:
                    logger.debug(f"Using PriceInfo for UIC {uic}: {price}")
                    return float(price)
            
            # Log détaillé pour débogage
            logger.warning(
                f"No price found for UIC {uic} "
                f"(Mid={quote.get('Mid')}, Bid={quote.get('Bid')}, Ask={quote.get('Ask')}, "
                f"Amount={quote.get('Amount')}, PriceTypeAsk={price_type_ask}, PriceTypeBid={price_type_bid})"
            )
            return None
        elif response.status_code == 401:
            error_text = response.text[:500] if hasattr(response, 'text') else 'No response text'
            logger.error(
                f"❌ {environment} MODE: Unauthorized (401) for UIC {uic}. "
                f"⚠️ This usually means the token is not valid for this environment. "
                f"Check if you're using a {'SIM token with LIVE URL' if environment == 'LIVE' else 'LIVE token with SIM URL'}. "
                f"Error: {error_text}"
            )
        else:
            error_text = response.text[:500] if hasattr(response, 'text') else 'No response text'
            logger.warning(f"❌ {environment} MODE: Saxo API error {response.status_code} for UIC {uic}, asset_type={asset_type}: {error_text}")
            
    except requests.exceptions.Timeout:
        logger.warning(f"Saxo API timeout for UIC {uic}")
    except Exception as e:
        logger.error(f"Saxo price error for UIC {uic}: {e}")
    
    return None


def get_binance_price(symbol: str) -> Optional[float]:
    """
    Récupère le prix actuel depuis l'API Binance.
    
    Args:
        symbol: Paire de trading (ex: 'BTCUSDT')
        
    Returns:
        Prix ou None si non disponible
    """
    if not symbol:
        return None
    
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": symbol.upper()},
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            return float(data.get("price", 0))
            
    except Exception as e:
        logger.debug(f"Binance price error for {symbol}: {e}")
    
    return None


# ==============================================================================
# 🎯 GÉNÉRATION DES TICKERS YAHOO
# ==============================================================================

def generate_y4_ticker(symbol: str) -> Optional[str]:
    """
    Y4: Génère le ticker Yahoo via MIC Mapping (méthode prioritaire).
    
    Format attendu du symbole: "BASE:MIC" (ex: "AAPL:XNAS", "MC:XPAR")
    
    Args:
        symbol: Symbole broker avec MIC
        
    Returns:
        Ticker Yahoo ou None
    """
    if ":" not in symbol:
        return None
    
    parts = symbol.split(":")
    if len(parts) < 2:
        return None
    
    base, mic = parts[0], parts[1].lower()
    
    # Vérifier si le MIC est dans le mapping
    suffix = get_yahoo_suffix(mic)
    if suffix is None:
        logger.debug(f"Unknown MIC: {mic} for symbol {symbol}")
        return None
    
    # Nettoyer le symbole de base
    clean_base = base.replace(" ", "-")
    
    # Gestion des classes d'actions (ex: "BRKa" -> "BRK-A")
    if re.search(r"[a-z]$", clean_base):
        clean_base = clean_base[:-1] + "-" + clean_base[-1].upper()
    
    return f"{clean_base}{suffix}"


def generate_y3_ticker(name: str) -> Optional[str]:
    """
    Y3: Recherche le ticker Yahoo via le nom de l'entreprise (fallback 1).
    
    Args:
        name: Nom de l'entreprise
        
    Returns:
        Ticker Yahoo trouvé ou None
    """
    if not name:
        return None
    
    # Nettoyer le nom
    clean_name = clean_company_name(name)
    
    if len(clean_name) < 2:
        return None
    
    return yahoo_search_by_name(clean_name)


def generate_y0_ticker(symbol: str) -> str:
    """
    Y0: Utilise le symbole brut sans MIC (fallback 2).
    
    Args:
        symbol: Symbole broker
        
    Returns:
        Symbole de base sans MIC
    """
    base = symbol.split(":")[0] if ":" in symbol else symbol
    return base.replace(" ", "-")


# ==============================================================================
# 🔍 VALIDATION D'UN ASSET
# ==============================================================================

def validate_single_asset(
    asset,
    broker_config: Dict[str, Any],
    tolerance_percent: float = DEFAULT_PRICE_TOLERANCE_PERCENT
) -> ValidationResult:
    """
    Valide un seul asset et trouve son symbole Yahoo correspondant.
    
    Processus en cascade:
    1. Y4 (MIC Mapping) - Prioritaire
    2. Y3 (Recherche par nom) - Fallback 1
    3. Y0 (Symbole brut) - Fallback 2
    
    Args:
        asset: Instance de AllAssets
        broker_config: Configuration du broker (access_token, etc.)
        tolerance_percent: Tolérance de prix en %
        
    Returns:
        ValidationResult avec le résultat
    """
    try:
        # === Récupérer le prix de référence (broker) ===
        ref_price = None
        
        if asset.platform == 'SAXO':
            if not asset.saxo_uic:
                logger.warning(f"Asset {asset.symbol}: Missing Saxo UIC")
                return ValidationResult(
                    yahoo_symbol='not_found',
                    status=ValidationStatus.ERROR,
                    error_message='Missing Saxo UIC'
                )
            
            access_token = broker_config.get('access_token', '')
            if not access_token:
                logger.warning(f"Asset {asset.symbol}: No access token in broker_config")
                return ValidationResult(
                    yahoo_symbol='not_found',
                    status=ValidationStatus.ERROR,
                    error_message='Missing access token'
                )
            
            logger.debug(f"Asset {asset.symbol}: Getting Saxo price for UIC {asset.saxo_uic}, asset_type={asset.asset_type or 'Stock'}")
            # Utiliser 'Stock' par défaut si asset_type est vide
            asset_type_for_request = asset.asset_type or 'Stock'
            ref_price = get_saxo_price(
                access_token=access_token,
                uic=asset.saxo_uic,
                asset_type=asset_type_for_request,
                # ✅ MIGRATION: Fallback changé de SIM vers LIVE
                base_url=broker_config.get('base_url', 'https://gateway.saxobank.com/openapi')
            )
            if ref_price is None:
                logger.warning(f"Asset {asset.symbol}: Failed to get Saxo price for UIC {asset.saxo_uic}")
            
        elif asset.platform == 'BINANCE':
            # Pour Binance, construire le symbole de trading
            trading_symbol = f"{asset.binance_base_asset}{asset.binance_quote_asset}"
            logger.debug(f"Asset {asset.symbol}: Getting Binance price for {trading_symbol}")
            ref_price = get_binance_price(trading_symbol)
            if ref_price is None:
                logger.warning(f"Asset {asset.symbol}: Failed to get Binance price for {trading_symbol}")
        else:
            logger.warning(f"Asset {asset.symbol}: Unknown platform {asset.platform}")
            ref_price = None
        
        if ref_price is None:
            return ValidationResult(
                yahoo_symbol='not_found',
                status=ValidationStatus.ERROR,
                error_message='Could not get reference price from broker'
            )
        
        # Calculer la tolérance absolue
        tolerance = ref_price * (tolerance_percent / 100)
        
        def price_matches(yahoo_price: Optional[float]) -> bool:
            """Vérifie si le prix Yahoo match avec le prix broker."""
            if yahoo_price is None:
                return False
            return abs(yahoo_price - ref_price) <= tolerance
        
        # === Étape 1: Y4 (MIC Mapping) - Prioritaire ===
        y4_ticker = generate_y4_ticker(asset.symbol)
        if y4_ticker:
            y4_price = get_yahoo_price(y4_ticker)
            if price_matches(y4_price):
                logger.debug(f"✅ Y4 match: {asset.symbol} -> {y4_ticker}")
                return ValidationResult(
                    yahoo_symbol=y4_ticker,
                    status=ValidationStatus.VALIDATED_Y4,
                    method='Y4_MIC',
                    yahoo_price=y4_price,
                    broker_price=ref_price
                )
        
        # === Étape 2: Y3 (Recherche par nom) - Fallback 1 ===
        y3_ticker = generate_y3_ticker(asset.name)
        if y3_ticker:
            y3_price = get_yahoo_price(y3_ticker)
            if price_matches(y3_price):
                logger.debug(f"✅ Y3 match: {asset.symbol} ({asset.name}) -> {y3_ticker}")
                return ValidationResult(
                    yahoo_symbol=y3_ticker,
                    status=ValidationStatus.VALIDATED_Y3,
                    method='Y3_NAME',
                    yahoo_price=y3_price,
                    broker_price=ref_price
                )
        
        # === Étape 3: Y0 (Symbole brut) - Fallback 2 ===
        y0_ticker = generate_y0_ticker(asset.symbol)
        if y0_ticker:
            y0_price = get_yahoo_price(y0_ticker)
            if price_matches(y0_price):
                logger.debug(f"✅ Y0 match: {asset.symbol} -> {y0_ticker}")
                return ValidationResult(
                    yahoo_symbol=y0_ticker,
                    status=ValidationStatus.VALIDATED_Y0,
                    method='Y0_RAW',
                    yahoo_price=y0_price,
                    broker_price=ref_price
                )
        
        # === Aucune correspondance trouvée ===
        logger.debug(f"❌ No match found for: {asset.symbol}")
        return ValidationResult(
            yahoo_symbol='not_found',
            status=ValidationStatus.NOT_FOUND,
            broker_price=ref_price
        )
        
    except Exception as e:
        logger.error(f"Validation error for {asset.symbol}: {e}")
        return ValidationResult(
            yahoo_symbol='not_found',
            status=ValidationStatus.ERROR,
            error_message=str(e)
        )


# ==============================================================================
# 🚀 FONCTION PRINCIPALE DE VALIDATION
# ==============================================================================

def validate_assets(
    all_assets: List,
    broker_name: str,
    asset_type: Optional[str] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    tolerance_percent: float = DEFAULT_PRICE_TOLERANCE_PERCENT,
    broker_config: Optional[Dict[str, Any]] = None,
    save_to_db: bool = True,
    verbose: bool = True
) -> ValidationStats:
    """
    Valide et enrichit une liste d'assets avec des symboles Yahoo Finance.
    
    Args:
        all_assets: Liste d'objets AllAssets à valider
        broker_name: Nom du broker ('SAXO', 'BINANCE', etc.)
        asset_type: Type d'actif à filtrer (optionnel)
        max_workers: Nombre de threads parallèles (2 recommandé)
        tolerance_percent: Tolérance de prix en %
        broker_config: Configuration du broker (access_token pour Saxo, etc.)
        save_to_db: Sauvegarder les résultats en base de données
        verbose: Afficher la progression
        
    Returns:
        ValidationStats avec les statistiques
    """
    stats = ValidationStats()
    
    # Configuration broker par défaut
    if broker_config is None:
        broker_config = {}
    
    # Filtrer les assets à valider
    assets_to_validate = [
        a for a in all_assets
        if a.platform == broker_name
        and (asset_type is None or a.asset_type == asset_type)
        and a.symbole_yahoo == 'Not_searched'
    ]
    
    # Assets ignorés (déjà validés ou manuels)
    skipped_count = len([
        a for a in all_assets
        if a.platform == broker_name
        and a.symbole_yahoo in ['manual']
    ])
    stats.skipped = skipped_count
    
    if not assets_to_validate:
        if verbose:
            print(f"⚠️ Aucun asset à valider pour {broker_name}")
        return stats
    
    stats.total = len(assets_to_validate)
    
    if verbose:
        print(f"\n🚀 Validation de {stats.total} assets {broker_name}...")
        print(f"   Tolérance: ±{tolerance_percent}%")
        print(f"   Workers: {max_workers}")
        if skipped_count > 0:
            print(f"   Ignorés (manual): {skipped_count}")
        print()
    
    # Validation parallèle
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                validate_single_asset, 
                asset, 
                broker_config, 
                tolerance_percent
            ): asset
            for asset in assets_to_validate
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            asset = futures[future]
            
            try:
                result = future.result()
                
                # Mettre à jour les statistiques
                if result.status == ValidationStatus.VALIDATED_Y4:
                    stats.validated_y4 += 1
                elif result.status == ValidationStatus.VALIDATED_Y3:
                    stats.validated_y3 += 1
                elif result.status == ValidationStatus.VALIDATED_Y0:
                    stats.validated_y0 += 1
                elif result.status == ValidationStatus.NOT_FOUND:
                    stats.not_found += 1
                elif result.status == ValidationStatus.ERROR:
                    stats.errors += 1
                
                # Sauvegarder en DB si demandé
                if save_to_db:
                    asset.symbole_yahoo = result.yahoo_symbol
                    asset.yahoo_validation_method = result.method
                    asset.yahoo_validated_at = timezone.now()
                    asset.save(update_fields=[
                        'symbole_yahoo', 
                        'yahoo_validation_method', 
                        'yahoo_validated_at'
                    ])
                
                # Afficher la progression
                if verbose and (i % PROGRESS_INTERVAL == 0 or i == stats.total):
                    success_rate = (stats.validated_total / i * 100) if i > 0 else 0
                    print(
                        f"✅ {i}/{stats.total} | "
                        f"Validés: {stats.validated_total} ({success_rate:.1f}%) | "
                        f"Not found: {stats.not_found}"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing {asset.symbol}: {e}")
                stats.errors += 1
    
    # Affichage final
    if verbose:
        print_validation_summary(stats)
    
    return stats


def print_validation_summary(stats: ValidationStats) -> None:
    """Affiche le résumé de la validation."""
    print("\n" + "=" * 80)
    print("📊 RÉSULTATS DE VALIDATION")
    print("=" * 80)
    print(f"Total traité: {stats.total}")
    print(f"✅ Validés Y4 (MIC): {stats.validated_y4}")
    print(f"✅ Validés Y3 (nom): {stats.validated_y3}")
    print(f"✅ Validés Y0 (brut): {stats.validated_y0}")
    print(f"✅ TOTAL VALIDÉS: {stats.validated_total} ({stats.success_rate:.1f}%)")
    print(f"❌ Non trouvés: {stats.not_found}")
    print(f"⚠️ Erreurs: {stats.errors}")
    if stats.skipped > 0:
        print(f"⏭️ Ignorés (manual): {stats.skipped}")
    print("=" * 80)


# ==============================================================================
# 🧹 FONCTIONS UTILITAIRES
# ==============================================================================

def clear_yahoo_cache() -> None:
    """Vide le cache des requêtes Yahoo."""
    get_yahoo_price.cache_clear()
    yahoo_search_by_name.cache_clear()
    logger.info("Yahoo cache cleared")


def get_cache_info() -> Dict[str, Any]:
    """Retourne les informations sur le cache."""
    return {
        'price_cache': get_yahoo_price.cache_info()._asdict(),
        'search_cache': yahoo_search_by_name.cache_info()._asdict(),
    }


def validate_single_symbol(
    symbol: str,
    name: str = '',
    mic: str = ''
) -> Optional[str]:
    """
    Validation rapide d'un symbole unique (sans vérification de prix).
    
    Utile pour la validation manuelle ou les tests.
    
    Args:
        symbol: Symbole de l'asset
        name: Nom de l'entreprise (optionnel)
        mic: Market Identifier Code (optionnel)
        
    Returns:
        Ticker Yahoo ou None
    """
    # Construire le symbole avec MIC si fourni
    full_symbol = f"{symbol}:{mic}" if mic else symbol
    
    # Essayer Y4
    y4 = generate_y4_ticker(full_symbol)
    if y4:
        price = get_yahoo_price(y4)
        if price is not None:
            return y4
    
    # Essayer Y3
    if name:
        y3 = generate_y3_ticker(name)
        if y3:
            price = get_yahoo_price(y3)
            if price is not None:
                return y3
    
    # Essayer Y0
    y0 = generate_y0_ticker(full_symbol)
    price = get_yahoo_price(y0)
    if price is not None:
        return y0
    
    return None

