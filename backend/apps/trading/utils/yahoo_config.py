"""
Configuration pour la validation Yahoo Finance.

Ce module contient le mapping MIC -> suffixes Yahoo et les constantes de configuration.
"""

# ==============================================================================
# ⚙️ CONSTANTES DE CONFIGURATION
# ==============================================================================

# Tolérance de prix pour la validation (en pourcentage)
DEFAULT_PRICE_TOLERANCE_PERCENT = 5.0  # ±5%

# Timeout des requêtes HTTP (en secondes)
REQUEST_TIMEOUT = 5

# Nombre de threads parallèles (2 = sweet spot pour éviter rate limiting Yahoo)
DEFAULT_MAX_WORKERS = 2

# Taille du cache LRU
CACHE_SIZE = 5000

# Intervalle d'affichage de progression
PROGRESS_INTERVAL = 50

# ==============================================================================
# 🌍 MAPPING MIC -> SUFFIXES YAHOO
# ==============================================================================
# MIC = Market Identifier Code (ISO 10383)
# Les suffixes sont utilisés pour construire les tickers Yahoo Finance

MIC_TO_YAHOO_SUFFIX = {
    # ============== US Markets ==============
    'xnys': '',       # New York Stock Exchange
    'xnas': '',       # NASDAQ
    'arcx': '',       # NYSE Arca
    'xase': '',       # NYSE American (ex-AMEX)
    'bats': '',       # BATS Global Markets
    'iexg': '',       # IEX
    'xnms': '',       # NASDAQ Global Market
    'xngs': '',       # NASDAQ Global Select
    'xncm': '',       # NASDAQ Capital Market
    'xphl': '',       # Philadelphia Stock Exchange
    'xcbo': '',       # Chicago Board Options Exchange
    
    # ============== Europe - Western ==============
    # France
    'xpar': '.PA',    # Euronext Paris
    'alxp': '.PA',    # Alternext Paris
    
    # Pays-Bas
    'xams': '.AS',    # Euronext Amsterdam
    
    # Belgique
    'xbru': '.BR',    # Euronext Brussels
    
    # Portugal
    'xlis': '.LS',    # Euronext Lisbon
    
    # UK & Ireland
    'xlon': '.L',     # London Stock Exchange
    'xlse': '.L',     # LSE alias
    'xice': '.IL',    # Irish Stock Exchange (euronext)
    
    # Allemagne
    'xetr': '.DE',    # XETRA
    'xfra': '.F',     # Frankfurt Stock Exchange
    'xber': '.BE',    # Berlin
    'xham': '.HM',    # Hamburg
    'xhan': '.HA',    # Hanover
    'xmun': '.MU',    # Munich
    'xstu': '.SG',    # Stuttgart
    'xdus': '.DU',    # Düsseldorf
    
    # Italie
    'xmil': '.MI',    # Borsa Italiana (Milan)
    'mtaa': '.MI',    # MTA Milan
    
    # Suisse
    'xswx': '.SW',    # SIX Swiss Exchange
    'xvtx': '.SW',    # SIX Swiss Exchange (alias)
    
    # Espagne
    'xmad': '.MC',    # Bolsa de Madrid
    'xbar': '.BC',    # Barcelona
    'xbil': '.BI',    # Bilbao
    'xval': '.VA',    # Valencia
    
    # ============== Europe - Nordic ==============
    'xhel': '.HE',    # Helsinki (Nasdaq Nordic)
    'xsto': '.ST',    # Stockholm (Nasdaq Nordic)
    'xosl': '.OL',    # Oslo Børs
    'xcse': '.CO',    # Copenhagen (Nasdaq Nordic)
    'xice': '.IC',    # Iceland
    'xris': '.RG',    # Riga
    'xlit': '.VS',    # Vilnius
    'xtal': '.TL',    # Tallinn
    
    # ============== Europe - Eastern ==============
    'xwar': '.WA',    # Warsaw
    'xpra': '.PR',    # Prague
    'xbud': '.BD',    # Budapest
    'xbse': '.RO',    # Bucharest
    'xlju': '.LJ',    # Ljubljana
    'xzag': '.ZG',    # Zagreb
    
    # ============== Europe - Other ==============
    'xath': '.AT',    # Athens
    'xist': '.IS',    # Istanbul
    'xmos': '.ME',    # Moscow
    'xkiv': '.KV',    # Kiev (Ukraine)
    
    # ============== Asia - East ==============
    # Japon
    'xtks': '.T',     # Tokyo Stock Exchange
    'xjpx': '.T',     # Japan Exchange (TSE alias)
    'xose': '.O',     # Osaka
    'xngo': '.N',     # Nagoya
    'xsap': '.S',     # Sapporo
    'xfka': '.F',     # Fukuoka
    
    # Chine
    'xssc': '.SS',    # Shanghai Stock Exchange (SSE)
    'xshg': '.SS',    # Shanghai alias
    'xshe': '.SZ',    # Shenzhen Stock Exchange
    'xsec': '.SZ',    # Shenzhen alias
    
    # Hong Kong
    'xhkg': '.HK',    # Hong Kong Stock Exchange
    
    # Taiwan
    'xtai': '.TW',    # Taiwan Stock Exchange
    'xtaf': '.TWO',   # Taiwan OTC
    
    # Corée du Sud
    'xkrx': '.KS',    # Korea Exchange (KOSPI)
    'xkos': '.KS',    # KOSPI alias
    'xkoe': '.KQ',    # KOSDAQ
    
    # ============== Asia - Southeast ==============
    'xses': '.SI',    # Singapore Exchange
    'xkls': '.KL',    # Kuala Lumpur
    'xbkk': '.BK',    # Bangkok
    'xidx': '.JK',    # Jakarta
    'xphs': '.PS',    # Philippine Stock Exchange
    'xhnx': '.VN',    # Ho Chi Minh
    
    # ============== Asia - South ==============
    'xbom': '.BO',    # Bombay Stock Exchange
    'xnse': '.NS',    # National Stock Exchange of India
    'xcol': '.CM',    # Colombo
    'xkar': '.KA',    # Karachi
    'xdha': '.BD',    # Dhaka
    
    # ============== Oceania ==============
    'xasx': '.AX',    # Australian Securities Exchange
    'xnze': '.NZ',    # New Zealand Exchange
    
    # ============== Americas ==============
    # Canada
    'xtse': '.TO',    # Toronto Stock Exchange
    'xtsx': '.TO',    # TSX alias
    'xcnq': '.CN',    # Canadian Securities Exchange
    'xtsv': '.V',     # TSX Venture
    'xneo': '.NE',    # NEO Exchange
    
    # Amérique Latine
    'xmex': '.MX',    # Bolsa Mexicana de Valores
    'xsao': '.SA',    # B3 São Paulo
    'xbue': '.BA',    # Buenos Aires
    'xsgo': '.SN',    # Santiago
    'xlim': '.LM',    # Lima
    'xbog': '.CL',    # Bogota
    
    # ============== Middle East ==============
    'xtae': '.TA',    # Tel Aviv Stock Exchange
    'xdfm': '.DU',    # Dubai Financial Market
    'xads': '.AD',    # Abu Dhabi
    'xsau': '.SR',    # Saudi (Tadawul)
    'xkuw': '.KW',    # Kuwait
    'xqat': '.QA',    # Qatar
    'xmus': '.OM',    # Muscat
    'xbah': '.BH',    # Bahrain
    'xjor': '.AM',    # Amman
    
    # ============== Africa ==============
    'xjse': '.JO',    # Johannesburg
    'xnai': '.NR',    # Nairobi
    'xbot': '.BW',    # Botswana
    'xcas': '.CS',    # Casablanca
    'xnig': '.NI',    # Nigerian Stock Exchange
    'xegy': '.CA',    # Egypt (Cairo)
}

# ==============================================================================
# 🏷️ ASSET TYPE MAPPING
# ==============================================================================
# Mapping des types d'assets Saxo vers des types normalisés

SAXO_ASSET_TYPE_MAPPING = {
    'Stock': 'Stock',
    'Etf': 'ETF',
    'Fund': 'Fund',
    'Bond': 'Bond',
    'CfdOnStock': 'CFD_Stock',
    'CfdOnIndex': 'CFD_Index',
    'CfdOnForex': 'CFD_Forex',
    'CfdOnCommodity': 'CFD_Commodity',
    'CfdOnCrypto': 'Crypto',
    'FxSpot': 'Forex',
    'FxForward': 'Forex',
    'ContractFuture': 'Future',
    'StockOption': 'Option',
}

# ==============================================================================
# 🔍 PATTERNS DE NETTOYAGE
# ==============================================================================
# Patterns à enlever du nom de l'entreprise pour la recherche Yahoo

NAME_CLEANUP_PATTERNS = [
    ' SA',
    ' Inc',
    ' Inc.',
    ' Corp',
    ' Corp.',
    ' Corporation',
    ' Ltd',
    ' Ltd.',
    ' Limited',
    ' PLC',
    ' Plc',
    ' AG',
    ' SE',
    ' NV',
    ' N.V.',
    ' SpA',
    ' S.p.A.',
    ' S.A.',
    ' GmbH',
    ' AB',
    ' ASA',
    ' Oyj',
    ' SARL',
    ' SAS',
    ' & Co',
    ' & Co.',
    ' - Class A',
    ' - Class B',
    ' - Class C',
    ' (Class A)',
    ' (Class B)',
    ' (Class C)',
    ' Registered',
    ' Common Stock',
    ' Ordinary Shares',
    ' ADR',
    ' ADS',
]

# ==============================================================================
# 🏦 BROKER CONFIGURATIONS
# ==============================================================================

BROKER_BASE_URLS = {
    'SAXO': {
        'live': 'https://gateway.saxobank.com/openapi',
        'sim': 'https://gateway.saxobank.com/sim/openapi',
    },
    'BINANCE': {
        'live': 'https://api.binance.com',
        'testnet': 'https://testnet.binance.vision',
    },
}

# ==============================================================================
# 📊 VALIDATION STATUS
# ==============================================================================

class ValidationStatus:
    """Statuts de validation possibles."""
    VALIDATED_Y4 = 'validated_y4'   # Via MIC mapping
    VALIDATED_Y3 = 'validated_y3'   # Via recherche par nom
    VALIDATED_Y0 = 'validated_y0'   # Via symbole brut
    NOT_FOUND = 'not_found'         # Non trouvé
    MANUAL = 'manual'               # Validation manuelle requise
    ERROR = 'error'                 # Erreur lors de la validation
    SKIPPED = 'skipped'             # Ignoré (déjà validé ou manuel)


# ==============================================================================
# 🔧 FONCTIONS UTILITAIRES
# ==============================================================================

def get_yahoo_suffix(mic: str) -> str | None:
    """
    Retourne le suffixe Yahoo pour un MIC donné.
    
    Args:
        mic: Market Identifier Code (ex: 'XPAR', 'xnas')
        
    Returns:
        Suffixe Yahoo (ex: '.PA', '') ou None si non trouvé
    """
    return MIC_TO_YAHOO_SUFFIX.get(mic.lower())


def clean_company_name(name: str) -> str:
    """
    Nettoie le nom de l'entreprise pour la recherche Yahoo.
    
    Args:
        name: Nom complet de l'entreprise
        
    Returns:
        Nom nettoyé
    """
    cleaned = name
    for pattern in NAME_CLEANUP_PATTERNS:
        cleaned = cleaned.replace(pattern, '')
    
    # Prendre la première partie si séparé par " - "
    if ' - ' in cleaned:
        cleaned = cleaned.split(' - ')[0]
    
    return cleaned.strip()


def is_us_market(mic: str) -> bool:
    """
    Vérifie si le MIC correspond à un marché américain.
    
    Args:
        mic: Market Identifier Code
        
    Returns:
        True si marché US
    """
    us_mics = {'xnys', 'xnas', 'arcx', 'xase', 'bats', 'iexg', 'xnms', 'xngs', 'xncm'}
    return mic.lower() in us_mics

