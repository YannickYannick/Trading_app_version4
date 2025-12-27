# 🎯 Système de Validation Yahoo Finance

## Vue d'ensemble

Le système de validation Yahoo Finance permet d'enrichir automatiquement le catalogue d'assets (`AllAssets`) avec les symboles Yahoo Finance correspondants. Il utilise un algorithme de validation en cascade qui compare les prix entre le broker source et Yahoo Finance.

## Architecture

```
apps/trading/
├── models/
│   └── assets.py              # Modèle AllAssets avec champs Yahoo
├── utils/
│   └── yahoo_config.py        # Configuration et MIC mapping
├── services/
│   └── yahoo_validator.py     # Logique de validation
└── management/commands/
    └── validate_yahoo_assets.py   # Django command
```

---

## 📊 Modèle AllAssets

### Nouveaux champs ajoutés

```python
class AllAssets(models.Model):
    # ... autres champs ...
    
    # Champ Yahoo Finance - symbole validé
    symbole_yahoo = models.CharField(
        max_length=50,
        default='Not_searched',
        db_index=True,
        help_text="Symbole Yahoo validé, 'not_found', 'manual', ou 'Not_searched'"
    )
    yahoo_validated_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date de dernière validation Yahoo"
    )
    yahoo_validation_method = models.CharField(
        max_length=20,
        blank=True,
        help_text="Méthode de validation: Y4 (MIC), Y3 (nom), Y0 (brut)"
    )
```

### Valeurs possibles de `symbole_yahoo`

| Valeur | Signification |
|--------|---------------|
| `Not_searched` | Asset non encore validé (défaut) |
| `not_found` | Aucune correspondance Yahoo trouvée |
| `manual` | Nécessite validation manuelle |
| `AAPL`, `MC.PA`, etc. | Symbole Yahoo validé |

### Propriétés utilitaires

```python
asset.needs_yahoo_validation  # True si symbole_yahoo == 'Not_searched'
asset.is_yahoo_validated      # True si symbole Yahoo valide
asset.is_yahoo_manual         # True si validation manuelle requise

# Méthode pour mettre à jour
asset.set_yahoo_symbol('AAPL', method='Y4_MIC')
```

---

## 🔍 Algorithme de Validation en Cascade

Le système teste **3 méthodes** dans l'ordre de priorité :

### 1. Y4 - MIC Mapping (Prioritaire)

Utilise le code MIC (Market Identifier Code) pour construire le ticker Yahoo.

```
Symbole Broker: "AAPL:XNAS"
      ↓
Extraire MIC: "XNAS"
      ↓
Mapper vers suffixe Yahoo: "" (vide pour US)
      ↓
Ticker Yahoo: "AAPL"
```

**Exemples :**
- `AAPL:XNAS` → `AAPL` (US)
- `MC:XPAR` → `MC.PA` (Paris)
- `SAP:XETR` → `SAP.DE` (Allemagne)

### 2. Y3 - Recherche par Nom (Fallback 1)

Recherche via l'API Yahoo Finance Search avec le nom de l'entreprise nettoyé.

```
Nom: "LVMH Moët Hennessy Louis Vuitton SE"
      ↓
Nettoyer: "LVMH Moët Hennessy Louis Vuitton"
      ↓
Recherche Yahoo API
      ↓
Ticker trouvé: "MC.PA"
```

### 3. Y0 - Symbole Brut (Fallback 2)

Utilise le symbole sans modification comme dernier recours.

```
Symbole: "AAPL:XNAS"
      ↓
Extraire base: "AAPL"
      ↓
Tester directement sur Yahoo
```

### Validation par Prix

Chaque méthode valide le ticker trouvé en comparant les prix :

```
|prix_yahoo - prix_broker| ≤ tolérance (±5%)
```

---

## 🌍 MIC Mapping

Le fichier `yahoo_config.py` contient **107 mappings** MIC → suffixes Yahoo :

```python
MIC_TO_YAHOO_SUFFIX = {
    # US Markets
    'xnys': '',      # NYSE
    'xnas': '',      # NASDAQ
    
    # Europe
    'xpar': '.PA',   # Paris
    'xlon': '.L',    # London
    'xetr': '.DE',   # XETRA
    'xmil': '.MI',   # Milan
    'xswx': '.SW',   # Swiss
    
    # Asia
    'xtks': '.T',    # Tokyo
    'xhkg': '.HK',   # Hong Kong
    'xssc': '.SS',   # Shanghai
    
    # ... et 97 autres marchés
}
```

---

## ⚙️ Configuration

### Constantes (`yahoo_config.py`)

```python
DEFAULT_PRICE_TOLERANCE_PERCENT = 5.0   # ±5%
REQUEST_TIMEOUT = 5                      # secondes
DEFAULT_MAX_WORKERS = 2                  # threads parallèles
CACHE_SIZE = 5000                        # entrées LRU cache
PROGRESS_INTERVAL = 50                   # affichage tous les 50 assets
```

---

## 🚀 Utilisation

### Via Management Command

```bash
# Validation basique
python manage.py validate_yahoo_assets --broker=SAXO --access-token=YOUR_TOKEN

# Avec filtres
python manage.py validate_yahoo_assets \
    --broker=SAXO \
    --asset-type=Stock \
    --tolerance=3.0 \
    --workers=2

# Mode dry-run (sans sauvegarder)
python manage.py validate_yahoo_assets --broker=SAXO --dry-run --limit=100

# Revalider les not_found
python manage.py validate_yahoo_assets --broker=SAXO --reset-not-found
```

### Options disponibles

| Option | Description | Défaut |
|--------|-------------|--------|
| `--broker` | Broker source (SAXO, BINANCE) | **Requis** |
| `--asset-type` | Filtrer par type (Stock, ETF...) | Tous |
| `--workers` | Threads parallèles | 2 |
| `--tolerance` | Tolérance prix en % | 5.0 |
| `--access-token` | Token Saxo OAuth2 | Env var |
| `--saxo-env` | Environnement (sim/live) | sim |
| `--limit` | Limiter le nombre d'assets | Tous |
| `--dry-run` | Ne pas sauvegarder en DB | False |
| `--clear-cache` | Vider le cache Yahoo | False |
| `--quiet` | Mode silencieux | False |
| `--reset-not-found` | Revalider les not_found | False |

### Via Code Python

```python
from apps.trading.models import AllAssets
from apps.trading.services import validate_assets

# Récupérer les assets à valider
assets = AllAssets.objects.filter(
    platform='SAXO',
    symbole_yahoo='Not_searched'
)

# Configuration Saxo
saxo_config = {
    'access_token': 'YOUR_SAXO_TOKEN',
    'base_url': 'https://gateway.saxobank.com/sim/openapi'
}

# Validation
stats = validate_assets(
    all_assets=list(assets),
    broker_name='SAXO',
    asset_type='Stock',
    max_workers=2,
    tolerance_percent=5.0,
    broker_config=saxo_config,
    save_to_db=True,
    verbose=True
)

print(f"Validés: {stats.validated_total} ({stats.success_rate:.1f}%)")
```

---

## 📊 Sortie Console

```
================================================================================
🎯 VALIDATION YAHOO FINANCE
================================================================================

📋 Configuration:
   Broker: SAXO
   Type: Stock
   Assets à traiter: 1000
   Tolérance: ±5.0%
   Workers: 2

🚀 Validation de 1000 assets SAXO...

✅ 50/1000 | Validés: 42 (84.0%) | Not found: 8
✅ 100/1000 | Validés: 87 (87.0%) | Not found: 13
...
✅ 1000/1000 | Validés: 876 (87.6%) | Not found: 124

================================================================================
✅ RÉSULTATS DE VALIDATION
================================================================================

📈 Statistiques:
   Total traité: 1000
   ✅ Validés Y4 (MIC): 734
   ✅ Validés Y3 (nom): 98
   ✅ Validés Y0 (brut): 44

   🎯 TOTAL VALIDÉS: 876 (87.6%)
   ❌ Non trouvés: 124
   ⚠️ Erreurs: 0

================================================================================
```

---

## 🧹 Fonctions Utilitaires

### Vider le cache

```python
from apps.trading.services import clear_yahoo_cache

clear_yahoo_cache()  # Vide le cache LRU
```

### Informations cache

```python
from apps.trading.services import get_cache_info

info = get_cache_info()
print(f"Prix: {info['price_cache']['hits']} hits")
print(f"Search: {info['search_cache']['hits']} hits")
```

### Validation manuelle d'un symbole

```python
from apps.trading.services import validate_single_symbol

# Trouver le ticker Yahoo pour un symbole
ticker = validate_single_symbol(
    symbol='AAPL',
    name='Apple Inc',
    mic='XNAS'
)
print(ticker)  # 'AAPL'
```

---

## ⚠️ Points d'Attention

### Rate Limiting
- Yahoo Finance limite les requêtes
- Utiliser **max 2 workers** pour éviter les blocages
- Le cache LRU réduit les appels répétés

### Tokens Saxo
- Token OAuth2 requis pour récupérer les prix Saxo
- Environnement sim vs live à configurer

### Assets Manuels
- Les assets avec `symbole_yahoo='manual'` sont **ignorés**
- Utilisé pour les cas où la validation automatique échoue

### Tolérance de Prix
- Par défaut ±5% entre prix broker et Yahoo
- Ajuster si les marchés sont volatils
- Certains assets ont des spreads importants

---

## 📁 Fichiers Créés

| Fichier | Description |
|---------|-------------|
| `models/assets.py` | Champs Yahoo ajoutés à AllAssets |
| `utils/yahoo_config.py` | Configuration et 107 MIC mappings |
| `services/yahoo_validator.py` | Logique de validation complète |
| `management/commands/validate_yahoo_assets.py` | Django command |
| `migrations/0004_add_yahoo_fields_to_allassets.py` | Migration DB |

---

## 🔗 Dépendances

```txt
yfinance>=0.2.0
requests>=2.31.0
```

Ces dépendances sont déjà dans `requirements.txt`.

