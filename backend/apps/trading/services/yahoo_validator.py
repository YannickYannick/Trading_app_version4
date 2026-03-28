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


def generate_y6_ticker(symbol: str) -> Optional[str]:
    """
    Y6: Crypto/Stablecoins avec suffixe -USD.
    
    Pour les cryptos Binance ou stablecoins, ajoute -USD pour Yahoo.
    Ex: BTC -> BTC-USD, ETH -> ETH-USD, USDC -> USDC-USD
    
    Args:
        symbol: Symbole broker
        
    Returns:
        Ticker Yahoo avec -USD ou None
    """
    base = symbol.split(":")[0] if ":" in symbol else symbol
    clean_base = base.replace(" ", "-").upper()
    
    # Liste de cryptos courantes (peut être étendue)
    crypto_symbols = {
        'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 
        'MATIC', 'AVAX', 'SHIB', 'LTC', 'UNI', 'LINK', 'ATOM',
        'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD'  # Stablecoins
    }
    
    # Vérifier si c'est un symbole crypto connu
    if clean_base in crypto_symbols or len(clean_base) <= 5:
        return f"{clean_base}-USD"
    
    return None


def generate_y7_ticker(symbol: str) -> Optional[str]:
    """
    Y7: FxSpot avec suffixe =X pour Yahoo Finance.
    
    Pour les paires forex, ajoute =X.
    Ex: EURUSD -> EURUSD=X, GBPUSD -> GBPUSD=X
    
    Args:
        symbol: Symbole broker (ex: EUR/USD ou EURUSD)
        
    Returns:
        Ticker Yahoo forex ou None
    """
    # Nettoyer le symbole (enlever les slashes et espaces)
    base = symbol.split(":")[0] if ":" in symbol else symbol
    clean_base = base.replace("/", "").replace(" ", "").upper()
    
    # Format forex typique: 6 caractères (3 pour base + 3 pour quote)
    if len(clean_base) == 6 and clean_base.isalpha():
        # Vérifier que ce sont des paires de devises connues
        forex_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD',
            'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'TRY', 'ZAR',
            'MXN', 'BRL', 'CNY', 'HKD', 'SGD', 'KRW', 'INR', 'RUB'
        }
        
        base_currency = clean_base[:3]
        quote_currency = clean_base[3:]
        
        if base_currency in forex_currencies and quote_currency in forex_currencies:
            return f"{clean_base}=X"
    
    return None


def generate_y8_ticker_via_saxo_search(
    asset,
    broker_config: Dict[str, Any]
) -> Optional[Tuple[str, float]]:
    """
    Y8: Recherche via SaxoBroker.search_assets() puis validation Yahoo.
    
    Utilisé principalement pour FxSpot quand les autres méthodes échouent.
    Recherche l'asset sur Saxo par nom, récupère l'UIC, le prix, puis trouve le symbole Yahoo.
    
    Args:
        asset: Instance de AllAssets
        broker_config: Configuration du broker avec access_token
        
    Returns:
        Tuple (yahoo_symbol, saxo_price) ou None
    """
    if asset.platform != 'SAXO':
        return None
    
    try:
        # Import ici pour éviter les imports circulaires
        from ..brokers.saxo import SaxoBroker
        from ..brokers.base import BrokerCredentials
        
        access_token = broker_config.get('access_token', '')
        if not access_token:
            return None
        
        # Créer une instance SaxoBroker
        credentials = BrokerCredentials(
            broker_name='SAXO',
            access_token=access_token,
            refresh_token=broker_config.get('refresh_token', ''),
            # URL LIVE par défaut
            api_base_url=broker_config.get('base_url', 'https://gateway.saxobank.com/openapi')
        )
        saxo_broker = SaxoBroker(credentials)
        
        # Rechercher l'asset par son nom
        search_query = asset.name or asset.symbol.split(':')[0]
        asset_types = ['FxSpot'] if asset.asset_type == 'FxSpot' else None
        
        logger.debug(f"Y8: Searching Saxo for '{search_query}' (asset_type={asset.asset_type})")
        
        search_results = saxo_broker.search_assets(
            query=search_query,
            asset_types=asset_types,
            limit=5
        )
        
        if not search_results:
            logger.debug(f"Y8: No search results for '{search_query}'")
            return None
        
        # Prendre le premier résultat qui match le symbole ou le nom
        for result in search_results:
            # Vérifier si c'est le bon asset (comparaison symbole ou UIC)
            if (result.symbol == asset.symbol or 
                (hasattr(result, 'uic') and result.uic == asset.saxo_uic)):
                
                # Récupérer le prix Saxo
                uic = result.uic if hasattr(result, 'uic') else asset.saxo_uic
                if not uic:
                    continue
                
                saxo_price = get_saxo_price(
                    access_token=access_token,
                    uic=uic,
                    asset_type=asset.asset_type or 'FxSpot',
                    base_url=credentials.api_base_url
                )
                
                if saxo_price is None:
                    continue
                
                # Construire le symbole Yahoo pour FxSpot
                if asset.asset_type == 'FxSpot':
                    # Ex: EUR/USD -> EURUSD=X
                    clean_symbol = result.symbol.replace('/', '').replace(' ', '')
                    yahoo_candidate = f"{clean_symbol}=X"
                    
                    # Vérifier que le prix Yahoo existe
                    yahoo_price = get_yahoo_price(yahoo_candidate)
                    if yahoo_price:
                        logger.info(f"✅ Y8 match via Saxo search: {asset.symbol} -> {yahoo_candidate}")
                        return (yahoo_candidate, saxo_price)
                
        logger.debug(f"Y8: No matching asset found in search results")
        return None
        
    except Exception as e:
        logger.error(f"Y8 error for {asset.symbol}: {e}")
        return None


def generate_y9_ticker(symbol: str) -> Optional[str]:
    """
    Y9: Variations avec tiret/point pour les classes d'actions.
    
    Gère les variations de symboles avec classes d'actions.
    Ex: BRK.B -> BRK-B, BF.A -> BF-A
    
    Args:
        symbol: Symbole broker
        
    Returns:
        Ticker Yahoo avec variation ou None
    """
    base = symbol.split(":")[0] if ":" in symbol else symbol
    
    # Variation 1: Point -> Tiret (BRK.B -> BRK-B)
    if "." in base:
        return base.replace(".", "-")
    
    # Variation 2: Tiret -> Point (rare, mais possible)
    if "-" in base:
        return base.replace("-", ".")
    
    return None


def generate_y10_ticker(symbol: str) -> Optional[str]:
    """
    Y10: Paires crypto/fiat avec tiret (ex: SOLEUR -> SOL-EUR, BTCEUR -> BTC-EUR).
    
    Pour les paires Binance crypto/fiat, Yahoo Finance utilise un tiret.
    Détecte les paires se terminant par une devise fiat et insère un tiret.
    
    Args:
        symbol: Symbole broker (ex: SOLEUR, BTCEUR)
        
    Returns:
        Ticker Yahoo avec tiret ou None
    """
    base = symbol.split(":")[0] if ":" in symbol else symbol
    clean_base = base.upper()
    
    # Liste des devises fiat courantes
    fiat_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'BRL', 'TRY', 'RUB', 'KRW']
    
    # Vérifier si le symbole se termine par une devise fiat
    for fiat in fiat_currencies:
        if clean_base.endswith(fiat) and len(clean_base) > len(fiat):
            # Extraire la partie crypto (avant la devise)
            crypto_part = clean_base[:-len(fiat)]
            # Construire avec tiret: BTC-EUR, SOL-EUR, etc.
            return f"{crypto_part}-{fiat}"
    
    return None


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
            # === Détection intelligente des paires Binance ===
            # 1. D'abord essayer le symbole tel quel (ex: SOLEUR, BTCEUR)
            # 2. Si échec, essayer d'ajouter des quotes USD (ex: BTC -> BTCUSDT)
            
            base_symbol = asset.symbol.split(':')[0].upper()
            ref_price = None
            
            # Étape 1: Essayer le symbole directement (pour les paires existantes)
            logger.debug(f"Trying Binance pair as-is: {base_symbol}")
            ref_price = get_binance_price(base_symbol)
            
            if ref_price is not None:
                logger.debug(f"✅ Found Binance price for {asset.symbol} using direct pair {base_symbol}: {ref_price}")
            else:
                # Étape 2: Essayer d'ajouter des quotes USD
                quotes_to_test = ['USDT', 'BUSD', 'USDC', 'USD']
                
                for quote in quotes_to_test:
                    # Éviter ex: USDCUSDC
                    if base_symbol == quote:
                        continue
                    
                    # Éviter d'ajouter USDT si le symbole se termine déjà par une devise connue
                    # Ex: SOLEUR ne doit pas devenir SOLEURUSDT
                    known_quotes = ['USDT', 'BUSD', 'USDC', 'USD', 'EUR', 'GBP', 'BRL', 'TRY', 'RUB']
                    if any(base_symbol.endswith(q) for q in known_quotes):
                        continue
                        
                    trading_symbol = f"{base_symbol}{quote}"
                    price = get_binance_price(trading_symbol)
                    
                    if price is not None:
                        ref_price = price
                        logger.debug(f"✅ Found Binance price for {asset.symbol} via {trading_symbol}: {price}")
                        break
            
            if ref_price is None:
                logger.warning(f"Asset {asset.symbol}: Failed to get Binance price (tried direct '{base_symbol}' and USD pairs)")
        else:
            logger.warning(f"Asset {asset.symbol}: Unknown platform {asset.platform}")
            ref_price = None
        
        
        # === Fallback pour assets sans prix Binance ===
        # Pour les stablecoins, ETFs, et autres assets non disponibles sur Binance,
        # on peut valider Yahoo sans comparaison de prix
        no_price_validation_mode = False
        
        if ref_price is None and asset.platform == 'BINANCE':
            # Détecter si c'est un stablecoin
            stablecoin_symbols = {'USDC', 'USDT', 'BUSD', 'DAI', 'TUSD', 'USDP'}
            asset_symbol_upper = asset.symbol.upper()
            
            if any(stable in asset_symbol_upper for stable in stablecoin_symbols):
                logger.info(f"🔄 Stablecoin detected for {asset.symbol}, using fallback mode with ref_price=1.00 USD")
                ref_price = 1.00  # Prix de référence par défaut pour les stablecoins
                # Tolérance plus large pour les stablecoins (±10% au lieu de 5%)
                tolerance_percent = max(tolerance_percent, 10.0)
            else:
                # Pour les ETFs et autres assets (ex: ETHW), permettre validation sans prix
                logger.info(f"🔄 No Binance price for {asset.symbol}, enabling no-price validation mode (ETF/non-crypto asset)")
                no_price_validation_mode = True
                # On va chercher le symbole Yahoo sans vérifier le prix
        
        # Si toujours pas de prix de référence ET pas en mode no-price, retourner une erreur
        if ref_price is None and not no_price_validation_mode:
            return ValidationResult(
                yahoo_symbol='not_found',
                status=ValidationStatus.ERROR,
                error_message='Could not get reference price from broker'
            )
        
        # Calculer la tolérance absolue (seulement si on a un prix de référence)
        tolerance = ref_price * (tolerance_percent / 100) if ref_price else 0
        
        def price_matches(yahoo_price: Optional[float]) -> bool:
            """Vérifie si le prix Yahoo match avec le prix broker."""
            if yahoo_price is None:
                return False
            
            # Mode sans validation de prix : accepter n'importe quel prix Yahoo valide
            if no_price_validation_mode:
                return yahoo_price > 0  # Juste vérifier que le prix existe
            
            # Mode normal : comparer avec le prix broker
            return abs(yahoo_price - ref_price) <= tolerance
        
        # === Étape 1: Y4 (MIC Mapping) - Prioritaire ===
        y4_ticker = generate_y4_ticker(asset.symbol)
        if y4_ticker:
            logger.info(f"🔍 Y4: Trying Yahoo symbol '{y4_ticker}' for {asset.symbol}")
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
            logger.info(f"🔍 Y3: Trying Yahoo symbol '{y3_ticker}' (from name '{asset.name}') for {asset.symbol}")
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
            logger.info(f"🔍 Y0: Trying Yahoo symbol '{y0_ticker}' for {asset.symbol}")
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
        
        # === Étape 4: Y6 (Crypto -USD) - Fallback 3 ===
        y6_ticker = generate_y6_ticker(asset.symbol)
        if y6_ticker:
            logger.info(f"🔍 Y6: Trying Yahoo symbol '{y6_ticker}' for {asset.symbol}")
            y6_price = get_yahoo_price(y6_ticker)
            if price_matches(y6_price):
                logger.debug(f"✅ Y6 match: {asset.symbol} -> {y6_ticker}")
                return ValidationResult(
                    yahoo_symbol=y6_ticker,
                    status=ValidationStatus.VALIDATED_Y0,  # Utiliser Y0 pour stats
                    method='Y6_CRYPTO_USD',
                    yahoo_price=y6_price,
                    broker_price=ref_price
                )
        
        # === Étape 5: Y7 (FX avec =X) - Fallback 4 ===
        y7_ticker = generate_y7_ticker(asset.symbol)
        if y7_ticker:
            logger.info(f"🔍 Y7: Trying Yahoo symbol '{y7_ticker}' for {asset.symbol}")
            y7_price = get_yahoo_price(y7_ticker)
            if price_matches(y7_price):
                logger.debug(f"✅ Y7 match: {asset.symbol} -> {y7_ticker}")
                return ValidationResult(
                    yahoo_symbol=y7_ticker,
                    status=ValidationStatus.VALIDATED_Y0,  # Utiliser Y0 pour stats
                    method='Y7_FOREX',
                    yahoo_price=y7_price,
                    broker_price=ref_price
                )
        
        # === Étape 6: Y8 (Saxo Search pour FxSpot) - Fallback 5 ===
        if asset.platform == 'SAXO' and asset.asset_type == 'FxSpot':
            y8_result = generate_y8_ticker_via_saxo_search(asset, broker_config)
            if y8_result:
                y8_ticker, y8_broker_price = y8_result
                y8_price = get_yahoo_price(y8_ticker)
                # Pour Y8, on a déjà le prix broker de la recherche
                if y8_price and price_matches(y8_price):
                    logger.debug(f"✅ Y8 match: {asset.symbol} -> {y8_ticker}")
                    return ValidationResult(
                        yahoo_symbol=y8_ticker,
                        status=ValidationStatus.VALIDATED_Y0,  # Utiliser Y0 pour stats
                        method='Y8_SAXO_SEARCH',
                        yahoo_price=y8_price,
                        broker_price=y8_broker_price
                    )
        
        
        # === Étape 7: Y9 (Variations symbole) - Fallback 6 ===
        y9_ticker = generate_y9_ticker(asset.symbol)
        if y9_ticker:
            logger.info(f"🔍 Y9: Trying Yahoo symbol '{y9_ticker}' for {asset.symbol}")
            y9_price = get_yahoo_price(y9_ticker)
            if price_matches(y9_price):
                logger.debug(f"✅ Y9 match: {asset.symbol} -> {y9_ticker}")
                return ValidationResult(
                    yahoo_symbol=y9_ticker,
                    status=ValidationStatus.VALIDATED_Y0,  # Utiliser Y0 pour stats
                    method='Y9_VARIATION',
                    yahoo_price=y9_price,
                    broker_price=ref_price
                )
        
        # === Étape 8: Y10 (Crypto/Fiat avec tiret) - Fallback 7 ===
        y10_ticker = generate_y10_ticker(asset.symbol)
        if y10_ticker:
            logger.info(f"🔍 Y10: Trying Yahoo symbol '{y10_ticker}' for {asset.symbol}")
            y10_price = get_yahoo_price(y10_ticker)
            if price_matches(y10_price):
                logger.debug(f"✅ Y10 match: {asset.symbol} -> {y10_ticker}")
                return ValidationResult(
                    yahoo_symbol=y10_ticker,
                    status=ValidationStatus.VALIDATED_Y0,  # Utiliser Y0 pour stats
                    method='Y10_CRYPTO_FIAT',
                    yahoo_price=y10_price,
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

