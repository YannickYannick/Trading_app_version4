"""
Saxo Bank Broker Implementation

Ce module implémente l'interface BrokerBase pour l'API Saxo Bank.
Il gère l'authentification OAuth2, la récupération des assets, des prix,
des positions, des trades et le placement d'ordres.
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from urllib.parse import urlencode, urlparse, urlunparse
from django.utils import timezone

from .base import (
    BrokerBase, 
    BrokerAsset, 
    BrokerPosition, 
    BrokerTrade, 
    BrokerOrder,
    OrderResult,
    BrokerError,
    BrokerAuthenticationError,
    BrokerAPIError,
    BrokerRateLimitError,
)

logger = logging.getLogger('trading_app.brokers')


class SaxoBroker(BrokerBase):
    """
    Client pour l'API Saxo Bank
    
    Implémente l'interface BrokerBase pour interagir avec l'API OpenAPI de Saxo Bank.
    Supporte l'authentification OAuth2 avec refresh token.
    
    Attributes:
        client_id: ID client OAuth2
        client_secret: Secret client OAuth2
        redirect_uri: URI de redirection OAuth2
        base_url: URL de base de l'API (live ou simulation)
        auth_url: URL d'authentification
        access_token: Token d'accès actuel
        refresh_token: Token de rafraîchissement
        token_expires_at: Date d'expiration du token
    """
    
    BROKER_NAME = "Saxo Bank"
    BROKER_TYPE = "saxo"
    
    # Mapping des types d'assets Saxo
    ASSET_TYPE_MAPPING = {
        'stock': 'Stock',
        'etf': 'Etf',
        'fund': 'Fund',
        'bond': 'Bond',
        'cfd': 'CfdOnStock',  # Par défaut pour CFD générique
        'cfdonstock': 'CfdOnStock',
        'cfdonindex': 'CfdOnIndex',
        'cfdonforex': 'CfdOnForex',
        'cfdonforward': 'CfdOnForward',
        'cfdonoption': 'CfdOnOption',
        'fx': 'FxSpot',  # Mapping pour FX générique
        'fxspot': 'FxSpot',
        'fxforward': 'FxForward',
        'fxoption': 'FxOption',
        'option': 'StockOption',
        'future': 'ContractFuture',
        'crypto': 'CfdOnCrypto',
    }
    
    def __init__(self, user, credentials: Dict[str, Any]):
        """
        Initialiser le client Saxo Bank
        
        Args:
            user: Django User instance
            credentials: Dictionnaire contenant:
                - client_id: ID client OAuth2
                - client_secret: Secret client OAuth2
                - redirect_uri: URI de redirection (optionnel)
                - environment: 'live' ou 'simulation' (défaut: simulation)
                - access_token: Token d'accès (optionnel)
                - refresh_token: Token de rafraîchissement (optionnel)
                - token_expires_at: Date d'expiration ISO (optionnel)
        """
        super().__init__(user, credentials)
        
        self.client_id = credentials.get('client_id')
        self.client_secret = credentials.get('client_secret')
        redirect_uri_raw = credentials.get('redirect_uri', 'http://localhost:8080/callback')
        # Normaliser l'URL : en minuscules pour le domaine (Saxo est sensible à la casse)
        if redirect_uri_raw:
            parsed = urlparse(redirect_uri_raw)
            # Reconstruire l'URL avec le domaine en minuscules
            normalized = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            self.redirect_uri = normalized
            logger.debug(f"Saxo redirect_uri normalized: {self.redirect_uri} (from: {redirect_uri_raw})")
        else:
            self.redirect_uri = 'http://localhost:8080/callback'
        
        # Environnement (live ou simulation)
        environment = credentials.get('environment', 'simulation')
        if environment == 'live':
            self.base_url = "https://gateway.saxobank.com/openapi"
            self.auth_url = "https://live.logonvalidation.net"
        else:
            self.base_url = "https://gateway.saxobank.com/sim/openapi"
            self.auth_url = "https://sim.logonvalidation.net"
        
        # Tokens
        self.access_token = credentials.get('access_token')
        self.refresh_token = credentials.get('refresh_token')
        self.token_expires_at = credentials.get('token_expires_at')
        
        # Client key pour certaines requêtes
        self.client_key = credentials.get('client_key')
        self.account_key = credentials.get('account_key')
        
        # Session HTTP
        self._session = requests.Session()
        
        logger.info(f"SaxoBroker initialized for environment: {environment}")
    
    # ==================== Authentication ====================
    
    def authenticate(self) -> bool:
        """
        Authentifier avec Saxo Bank
        
        Tente d'utiliser le token existant ou de le rafraîchir.
        
        Returns:
            True si authentifié avec succès, False sinon
        """
        try:
            # Si token valide, pas besoin de ré-authentifier
            if self.is_authenticated():
                logger.debug("Saxo: Already authenticated with valid token")
                return True
            
            # Sinon, utiliser refresh token
            if self.refresh_token:
                logger.info("Saxo: Refreshing token...")
                return self._refresh_token()
            
            logger.warning("Saxo: No refresh token available, authentication required")
            return False
            
        except Exception as e:
            logger.error(f"Saxo authentication error: {e}")
            raise BrokerAuthenticationError(f"Authentication failed: {e}")
    
    def is_authenticated(self) -> bool:
        """
        Vérifier si le token est valide
        
        Returns:
            True si le token est valide et non expiré
        """
        if not self.access_token:
            return False
        
        if self.token_expires_at:
            try:
                from ..utils.token_utils import parse_iso_datetime
                expires_at = parse_iso_datetime(self.token_expires_at)
                if expires_at:
                    # Ajouter une marge de 5 minutes
                    now = timezone.now()
                    if expires_at.tzinfo:
                        now = now.astimezone(expires_at.tzinfo)
                    elif now.tzinfo:
                        expires_at = timezone.make_aware(expires_at) if expires_at.tzinfo is None else expires_at
                    if now >= expires_at - timedelta(minutes=5):
                        return False
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse token expiry: {e}")
                return False
        
        return True
    
    def refresh_authentication(self) -> bool:
        """
        Rafraîchir l'authentification (implémentation de l'interface abstraite).
        
        Returns:
            True si le rafraîchissement a réussi
        """
        return self._refresh_token()
    
    def _refresh_token(self) -> bool:
        """
        Rafraîchir le token d'accès
        
        Returns:
            True si le rafraîchissement a réussi
        """
        try:
            url = f"{self.auth_url}/token"
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }
            
            response = self._session.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.refresh_token = token_data.get('refresh_token', self.refresh_token)
            
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = (timezone.now() + timedelta(seconds=expires_in)).isoformat()
            
            self._authenticated = True
            logger.info("Saxo: Token refreshed successfully")
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Saxo token refresh HTTP error: {e}")
            if e.response.status_code == 401:
                raise BrokerAuthenticationError("Refresh token expired or invalid")
            raise BrokerAPIError(f"Token refresh failed: {e}")
        except Exception as e:
            logger.error(f"Saxo token refresh error: {e}")
            raise BrokerAuthenticationError(f"Token refresh failed: {e}")
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Obtenir l'URL d'autorisation OAuth2
        
        Args:
            state: État pour CSRF protection
            
        Returns:
            URL d'autorisation
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
        }
        if state:
            params['state'] = state
        
        return f"{self.auth_url}/authorize?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Échanger le code d'autorisation contre des tokens
        
        Args:
            code: Code d'autorisation OAuth2
            
        Returns:
            Dictionnaire avec access_token, refresh_token, etc.
        """
        try:
            url = f"{self.auth_url}/token"
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri,
            }
            
            response = self._session.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Mettre à jour les tokens
            self.access_token = token_data['access_token']
            self.refresh_token = token_data.get('refresh_token')
            
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = (timezone.now() + timedelta(seconds=expires_in)).isoformat()
            
            self._authenticated = True
            
            return {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_expires_at': self.token_expires_at,
                'expires_in': expires_in,
            }
            
        except Exception as e:
            logger.error(f"Saxo code exchange error: {e}")
            raise BrokerAuthenticationError(f"Code exchange failed: {e}")
    
    # ==================== API Request Helper ====================
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None, 
        data: Dict = None,
        json_data: Dict = None,
    ) -> Dict:
        """
        Faire une requête authentifiée à l'API Saxo
        
        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint de l'API (sans le base_url)
            params: Paramètres de requête
            data: Données de formulaire
            json_data: Données JSON
            
        Returns:
            Réponse JSON de l'API
        """
        # S'assurer d'être authentifié
        if not self.is_authenticated():
            if not self.authenticate():
                raise BrokerAuthenticationError("Not authenticated")
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        
        if json_data:
            headers["Content-Type"] = "application/json"
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=30,
            )
            
            # Gérer les erreurs HTTP
            if response.status_code == 401:
                # Token expiré, essayer de rafraîchir
                if self._refresh_token():
                    # Réessayer la requête
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    response = self._session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        data=data,
                        json=json_data,
                        timeout=30,
                    )
                else:
                    raise BrokerAuthenticationError("Token refresh failed")
            
            if response.status_code == 429:
                raise BrokerRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            # Certaines réponses peuvent être vides
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Saxo API HTTP error: {e}")
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
            raise BrokerAPIError(f"API request failed: {e} - {error_detail}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Saxo API request error: {e}")
            raise BrokerAPIError(f"Request failed: {e}")
    
    # ==================== Assets ====================
    
    def get_assets(
        self, 
        asset_type: str = "Stock", 
        keywords: str = "", 
        limit: int = 20000,
        exchange_id: str = None,
        **kwargs
    ) -> List[BrokerAsset]:
        """
        Récupérer la liste des assets depuis Saxo avec pagination
        
        Args:
            asset_type: Type d'asset (Stock, Etf, CfdOnStock, etc.)
            keywords: Mots-clés de recherche (si fourni, pas de pagination)
            limit: Nombre maximum de résultats (défaut: 20000)
            exchange_id: ID de la bourse (optionnel)
            
        Returns:
            Liste de BrokerAsset
        """
        try:
            # Mapper le type d'asset
            asset_type_lower = asset_type.lower() if asset_type else ''
            saxo_asset_type = self.ASSET_TYPE_MAPPING.get(
                asset_type_lower, 
                asset_type  # Utiliser le type original si non trouvé dans le mapping
            )
            
            # Si le type n'est toujours pas valide après mapping, logger un avertissement
            if saxo_asset_type == asset_type and asset_type_lower not in self.ASSET_TYPE_MAPPING:
                logger.warning(f"Saxo: Asset type '{asset_type}' not in mapping, using as-is")
            
            # Limite maximale pour la pagination
            limit_total = min(limit, 20000)
            batch_size = 1000  # Taille des lots pour la pagination
            
            # Si keywords est fourni, on fait une recherche simple sans pagination
            if keywords:
                params = {
                    "AssetTypes": saxo_asset_type,
                    "$top": limit_total,
                    "Keywords": keywords,
                }
                
                if exchange_id:
                    params["ExchangeId"] = exchange_id
                
                data = self._make_request('GET', '/ref/v1/instruments', params=params)
                all_items = data.get('Data', [])
            else:
                # Pagination pour récupérer jusqu'à limit_total actifs
                all_items = []
                skip = 0
                
                while len(all_items) < limit_total:
                    params = {
                        "AssetTypes": saxo_asset_type,
                        "$top": batch_size,
                        "$skip": skip,
                    }
                    
                    if exchange_id:
                        params["ExchangeId"] = exchange_id
                    
                    try:
                        data = self._make_request('GET', '/ref/v1/instruments', params=params)
                        batch = data.get('Data', [])
                        
                        if not batch:
                            # Plus de données disponibles
                            break
                        
                        all_items.extend(batch)
                        skip += batch_size
                        
                        # Si on a reçu moins que batch_size, on a atteint la fin
                        if len(batch) < batch_size:
                            break
                            
                    except BrokerAPIError as e:
                        # En cas d'erreur, on retourne ce qu'on a déjà récupéré
                        logger.warning(f"Saxo: Error during pagination at skip={skip}: {e}")
                        break
            
            # Limiter à limit_total
            all_items = all_items[:limit_total]
            
            # Convertir en BrokerAsset
            assets = []
            for item in all_items:
                asset = BrokerAsset(
                    symbol=item.get('Symbol', ''),
                    name=item.get('Description', ''),
                    asset_type=item.get('AssetType', asset_type),
                    exchange=item.get('ExchangeId', ''),
                    currency=item.get('CurrencyCode', 'USD'),
                    broker_id=str(item.get('Uic', '')),
                    is_tradable=item.get('IsTradable', True),
                    raw_data={
                        'uic': item.get('Uic'),
                        'exchange_id': item.get('ExchangeId'),
                        'country_code': item.get('CountryCode'),
                        'primary_listing': item.get('PrimaryListing'),
                        'group_id': item.get('GroupId'),
                        'lot_size': item.get('LotSize'),
                        'tick_size': item.get('TickSize'),
                    }
                )
                assets.append(asset)
            
            logger.info(f"Saxo: Retrieved {len(assets)} assets (limit: {limit_total})")
            return assets
            
        except BrokerError:
            raise
        except Exception as e:
            logger.error(f"Saxo get_assets error: {e}")
            raise BrokerAPIError(f"Failed to get assets: {e}")
    
    def search_assets(
        self, 
        query: str, 
        asset_types: List[str] = None,
        limit: int = 20
    ) -> List[BrokerAsset]:
        """
        Rechercher des assets par mot-clé
        
        Args:
            query: Terme de recherche
            asset_types: Types d'assets à rechercher
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de BrokerAsset
        """
        if asset_types is None:
            asset_types = ['Stock', 'Etf', 'CfdOnStock']
        
        all_assets = []
        for asset_type in asset_types:
            assets = self.get_assets(
                asset_type=asset_type,
                keywords=query,
                limit=limit // len(asset_types)
            )
            all_assets.extend(assets)
        
        return all_assets[:limit]
    
    # ==================== Prices ====================
    
    def get_asset_price(
        self, 
        symbol: str, 
        uic: int = None, 
        asset_type: str = "Stock",
        **kwargs
    ) -> Optional[Decimal]:
        """
        Récupérer le prix d'un asset
        
        Args:
            symbol: Symbole de l'asset
            uic: UIC Saxo de l'asset (plus précis)
            asset_type: Type d'asset
            
        Returns:
            Prix de l'asset ou None
        """
        try:
            # Si pas d'UIC, essayer de le trouver
            if uic is None:
                uic = self._get_uic_from_symbol(symbol, asset_type)
                if uic is None:
                    logger.warning(f"Saxo: Could not find UIC for {symbol}")
                    return None
            
            # Mapper le type d'asset
            saxo_asset_type = self.ASSET_TYPE_MAPPING.get(
                asset_type.lower(), 
                asset_type
            )
            
            params = {
                "Uic": uic,
                "AssetType": saxo_asset_type,
            }
            
            data = self._make_request('GET', '/trade/v1/infoprices', params=params)
            
            quote = data.get("Quote", {})
            if quote:
                # Prendre Ask, puis Mid, puis Bid
                price = quote.get("Ask") or quote.get("Mid") or quote.get("Bid")
                if price:
                    return Decimal(str(price))
            
            return None
            
        except BrokerError:
            raise
        except Exception as e:
            logger.error(f"Saxo get_asset_price error: {e}")
            return None
    
    def get_prices_batch(
        self, 
        assets: List[Dict[str, Any]]
    ) -> Dict[str, Decimal]:
        """
        Récupérer les prix de plusieurs assets en batch
        
        Args:
            assets: Liste de dicts avec 'uic' et 'asset_type'
            
        Returns:
            Dictionnaire {symbol: prix}
        """
        prices = {}
        
        # Saxo supporte les requêtes batch via subscriptions
        # Pour l'instant, faire des requêtes individuelles
        for asset in assets:
            try:
                uic = asset.get('uic')
                symbol = asset.get('symbol', str(uic))
                asset_type = asset.get('asset_type', 'Stock')
                
                price = self.get_asset_price(symbol, uic=uic, asset_type=asset_type)
                if price:
                    prices[symbol] = price
                    
            except Exception as e:
                logger.warning(f"Saxo: Error getting price for {symbol}: {e}")
                continue
        
        return prices
    
    def get_price_details(
        self, 
        uic: int, 
        asset_type: str = "Stock"
    ) -> Dict[str, Any]:
        """
        Récupérer les détails de prix complets
        
        Args:
            uic: UIC de l'asset
            asset_type: Type d'asset
            
        Returns:
            Dictionnaire avec tous les détails de prix
        """
        try:
            saxo_asset_type = self.ASSET_TYPE_MAPPING.get(
                asset_type.lower(), 
                asset_type
            )
            
            params = {
                "Uic": uic,
                "AssetType": saxo_asset_type,
                "FieldGroups": "PriceInfo,PriceInfoDetails,Quote,Greeks",
            }
            
            data = self._make_request('GET', '/trade/v1/infoprices', params=params)
            
            return {
                'quote': data.get('Quote', {}),
                'price_info': data.get('PriceInfo', {}),
                'price_info_details': data.get('PriceInfoDetails', {}),
                'greeks': data.get('Greeks', {}),
                'last_updated': data.get('LastUpdated'),
            }
            
        except Exception as e:
            logger.error(f"Saxo get_price_details error: {e}")
            return {}
    
    # ==================== Positions ====================
    
    def _get_account_keys(self) -> Dict[str, Optional[str]]:
        """
        Récupère ClientKey et AccountKey depuis les comptes.
        
        Returns:
            Dict avec 'client_key' et 'account_key'
        """
        try:
            account_params = {}
            if self.client_key:
                account_params['ClientKey'] = self.client_key
            
            account_data = self._make_request('GET', '/port/v1/accounts', params=account_params)
            
            accounts = account_data.get('Data', [])
            if not accounts:
                logger.warning("No accounts found in Saxo response")
                return {'client_key': self.client_key, 'account_key': self.account_key}
            
            primary_account = accounts[0]
            account_key = primary_account.get('AccountKey')
            client_key_from_account = primary_account.get('ClientKey')
            
            # Utiliser le ClientKey de la réponse si disponible, sinon celui des credentials
            client_key_to_use = client_key_from_account or self.client_key
            
            return {
                'client_key': client_key_to_use,
                'account_key': account_key or self.account_key
            }
        except Exception as e:
            logger.warning(f"Error getting account keys: {e}, using credentials values")
            return {'client_key': self.client_key, 'account_key': self.account_key}
    
    def get_positions(self, **kwargs) -> List[BrokerPosition]:
        """
        Récupérer les positions ouvertes
        
        Returns:
            Liste de BrokerPosition
        """
        try:
            # Récupérer les clés nécessaires
            keys = self._get_account_keys()
            
            params = {}
            if keys.get('client_key'):
                params['ClientKey'] = keys['client_key']
            if keys.get('account_key'):
                params['AccountKey'] = keys['account_key']
            
            # Les deux sont requis par l'API Saxo
            if not params.get('ClientKey'):
                logger.warning("ClientKey is required for positions but not available")
            
            data = self._make_request('GET', '/port/v1/positions', params=params)
            
            positions = []
            for item in data.get('Data', []):
                position_base = item.get('PositionBase', {})
                position_view = item.get('PositionView', {})
                
                # Extraire le symbole
                symbol = position_base.get('Symbol', '').strip()
                uic = position_base.get('Uic')
                asset_type = position_base.get('AssetType', 'Stock')
                
                # Si le symbole est vide, essayer de le récupérer depuis l'UIC
                if not symbol and uic:
                    try:
                        symbol_from_uic = self._get_symbol_from_uic(uic, asset_type)
                        if symbol_from_uic:
                            symbol = symbol_from_uic
                            logger.debug(f"Saxo: Recovered symbol {symbol} from UIC {uic}")
                        else:
                            logger.warning(f"Saxo: Could not recover symbol for UIC {uic}")
                    except Exception as e:
                        logger.warning(f"Saxo: Error recovering symbol from UIC {uic}: {e}")
                
                # Si toujours pas de symbole, utiliser un identifiant de fallback
                if not symbol:
                    position_id = str(item.get('PositionId', ''))
                    uic_str = str(uic) if uic else 'UNKNOWN'
                    symbol = f"UIC_{uic_str}" if uic else f"POS_{position_id[:8]}"
                    logger.warning(f"Saxo: Position {position_id} has no symbol, using fallback: {symbol}")
                
                # Déterminer le side (LONG ou SHORT) à partir de la quantité
                amount = Decimal(str(position_base.get('Amount', 0)))
                side = 'LONG' if amount >= 0 else 'SHORT'
                
                # Extraire les prix et PnL
                entry_price = Decimal(str(position_view.get('AverageOpenPrice', 0)))
                current_price = Decimal(str(position_view.get('CurrentPrice', 0)))
                pnl = Decimal(str(position_view.get('ProfitLossOnTrade', 0)))
                
                # Calculer le PnL en pourcentage
                pnl_percent = Decimal('0')
                if entry_price and entry_price > 0:
                    pnl_percent = ((current_price - entry_price) / entry_price) * Decimal('100')
                
                position = BrokerPosition(
                    symbol=symbol,  # Utiliser le symbole récupéré ou le fallback
                    quantity=abs(amount),  # Quantité absolue
                    entry_price=entry_price,
                    current_price=current_price,
                    side=side,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    broker_position_id=str(item.get('PositionId', '')),
                    raw_data={
                        'uic': uic,
                        'asset_type': asset_type,
                        'account_id': position_base.get('AccountId'),
                        'status': position_base.get('Status'),
                        'execution_time': position_base.get('ExecutionTimeOpen'),
                        'value_date': position_base.get('ValueDate'),
                        'exposure': position_view.get('Exposure'),
                        'market_value': position_view.get('MarketValue'),
                        'currency': position_base.get('Currency', 'USD'),
                        'original_symbol': position_base.get('Symbol', ''),  # Garder le symbole original même s'il est vide
                    }
                )
                positions.append(position)
            
            logger.info(f"Saxo: Retrieved {len(positions)} positions")
            return positions
            
        except BrokerError:
            raise
        except Exception as e:
            logger.error(f"Saxo get_positions error: {e}")
            raise BrokerAPIError(f"Failed to get positions: {e}")
    
    def get_position_details(self, position_id: str) -> Optional[BrokerPosition]:
        """
        Récupérer les détails d'une position spécifique
        
        Args:
            position_id: ID de la position
            
        Returns:
            BrokerPosition ou None
        """
        try:
            params = {}
            if self.client_key:
                params['ClientKey'] = self.client_key
            
            data = self._make_request(
                'GET', 
                f'/port/v1/positions/{position_id}',
                params=params
            )
            
            if not data:
                return None
            
            position_base = data.get('PositionBase', {})
            position_view = data.get('PositionView', {})
            
            # Extraire le symbole
            symbol = position_base.get('Symbol', '').strip()
            uic = position_base.get('Uic')
            asset_type = position_base.get('AssetType', 'Stock')
            
            # Si le symbole est vide, essayer de le récupérer depuis l'UIC
            if not symbol and uic:
                try:
                    symbol_from_uic = self._get_symbol_from_uic(uic, asset_type)
                    if symbol_from_uic:
                        symbol = symbol_from_uic
                        logger.debug(f"Saxo: Recovered symbol {symbol} from UIC {uic}")
                except Exception as e:
                    logger.warning(f"Saxo: Error recovering symbol from UIC {uic}: {e}")
            
            # Si toujours pas de symbole, utiliser un identifiant de fallback
            if not symbol:
                position_id = str(data.get('PositionId', ''))
                uic_str = str(uic) if uic else 'UNKNOWN'
                symbol = f"UIC_{uic_str}" if uic else f"POS_{position_id[:8]}"
                logger.warning(f"Saxo: Position {position_id} has no symbol, using fallback: {symbol}")
            
            # Déterminer le side (LONG ou SHORT) à partir de la quantité
            amount = Decimal(str(position_base.get('Amount', 0)))
            side = 'LONG' if amount >= 0 else 'SHORT'
            
            # Extraire les prix et PnL
            entry_price = Decimal(str(position_view.get('AverageOpenPrice', 0)))
            current_price = Decimal(str(position_view.get('CurrentPrice', 0)))
            pnl = Decimal(str(position_view.get('ProfitLossOnTrade', 0)))
            
            # Calculer le PnL en pourcentage
            pnl_percent = Decimal('0')
            if entry_price and entry_price > 0:
                pnl_percent = ((current_price - entry_price) / entry_price) * Decimal('100')
            
            return BrokerPosition(
                symbol=symbol,  # Utiliser le symbole récupéré ou le fallback
                quantity=abs(amount),  # Quantité absolue
                entry_price=entry_price,
                current_price=current_price,
                side=side,
                pnl=pnl,
                pnl_percent=pnl_percent,
                broker_position_id=str(data.get('PositionId', '')),
                raw_data={
                    'uic': uic,
                    'asset_type': asset_type,
                    'account_id': position_base.get('AccountId'),
                    'status': position_base.get('Status'),
                    'execution_time': position_base.get('ExecutionTimeOpen'),
                    'value_date': position_base.get('ValueDate'),
                    'exposure': position_view.get('Exposure'),
                    'market_value': position_view.get('MarketValue'),
                    'currency': position_base.get('Currency', 'USD'),
                    'original_symbol': position_base.get('Symbol', ''),  # Garder le symbole original même s'il est vide
                }
            )
            
        except Exception as e:
            logger.error(f"Saxo get_position_details error: {e}")
            return None
    
    # ==================== Trades ====================
    
    def get_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 10000,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Récupérer l'historique des transactions depuis hist/v1/transactions.
        
        Cet endpoint fournit un niveau de détail supérieur à hist/v3/positions
        et permet de reconstruire les positions avec plus de précision.
        
        Note: L'API Saxo REQUIERT FromDate et ToDate. Si non fournis, utilise
        les 30 derniers jours par défaut.
        
        Args:
            from_date: Date de début (format ISO, optionnel - défaut: 30 jours avant aujourd'hui)
            to_date: Date de fin (format ISO, optionnel - défaut: aujourd'hui)
            limit: Nombre maximum de transactions à récupérer
            
        Returns:
            Liste de transactions brutes depuis l'API Saxo
        """
        try:
            from datetime import datetime, timedelta
            
            # Récupérer les clés nécessaires
            keys = self._get_account_keys()
            
            params = {
                "$top": min(limit, 10000),  # Limite max de l'API
            }
            
            if keys.get('client_key'):
                params['ClientKey'] = keys['client_key']
            if keys.get('account_key'):
                params['AccountKey'] = keys['account_key']
            
            # L'API Saxo REQUIERT FromDate et ToDate
            # Format attendu: YYYY-MM-DD (date seulement, sans heure)
            # Si non fournis, utiliser les 30 derniers jours par défaut
            if not from_date:
                from_date_dt = datetime.utcnow() - timedelta(days=30)
                # Format date seulement YYYY-MM-DD
                from_date = from_date_dt.strftime('%Y-%m-%d')
            elif 'T' in from_date:
                # Si format ISO avec heure, extraire seulement la date
                from_date = from_date.split('T')[0]
            
            if not to_date:
                to_date_dt = datetime.utcnow()
                # Format date seulement YYYY-MM-DD
                to_date = to_date_dt.strftime('%Y-%m-%d')
            elif 'T' in to_date:
                # Si format ISO avec heure, extraire seulement la date
                to_date = to_date.split('T')[0]
            
            params['FromDate'] = from_date
            params['ToDate'] = to_date
            
            # ClientKey est requis par l'API Saxo
            if not params.get('ClientKey'):
                logger.warning("ClientKey is required for transactions but not available")
            
            logger.debug(f"Fetching transactions from {from_date} to {to_date}")
            
            # Récupérer les transactions
            data = self._make_request('GET', '/hist/v1/transactions', params=params)
            
            transactions = data.get('Data', [])
            
            logger.info(f"Saxo: Retrieved {len(transactions)} transactions")
            return transactions
            
        except BrokerError:
            raise
        except Exception as e:
            logger.error(f"Saxo get_transactions error: {e}")
            raise BrokerAPIError(f"Failed to get transactions: {e}")
    
    def get_trades(self, limit: int = 50, **kwargs) -> List[BrokerTrade]:
        """
        Récupérer l'historique des trades depuis les transactions.
        
        Utilise hist/v1/transactions pour avoir un historique complet et détaillé
        des trades, incluant les clôtures partielles et toutes les transactions.
        
        Args:
            limit: Nombre maximum de trades à récupérer
            from_date: Date de début (optionnel)
            to_date: Date de fin (optionnel)
            symbol: Symbole à filtrer (optionnel)
            
        Returns:
            Liste de BrokerTrade
        """
        try:
            from datetime import datetime, timedelta
            
            # Récupérer les paramètres de date
            from_date = kwargs.get('from_date')
            to_date = kwargs.get('to_date')
            symbol_filter = kwargs.get('symbol')
            
            # Si pas de dates spécifiées, utiliser les 90 derniers jours
            if not from_date or not to_date:
                if not to_date:
                    to_date_dt = datetime.utcnow()
                    to_date = to_date_dt.strftime('%Y-%m-%d')
                if not from_date:
                    from_date_dt = datetime.utcnow() - timedelta(days=90)
                    from_date = from_date_dt.strftime('%Y-%m-%d')
            
            # Récupérer les transactions
            transactions = self.get_transactions(
                from_date=from_date,
                to_date=to_date,
                limit=min(limit * 5, 10000)  # Plus de transactions que de trades (certaines sont des frais)
            )
            
            # Convertir les transactions en BrokerTrade
            trades = []
            seen_trade_ids = set()
            
            for txn in transactions:
                # Filtrer les transactions de type Trade
                tx_type = txn.get('TransactionType', '')
                if tx_type != 'Trade':
                    continue
                
                # Les données de trade sont dans le tableau Trades[]
                trades_array = txn.get('Trades', [])
                if not trades_array:
                    continue
                
                # Extraire les infos de l'instrument
                instrument = txn.get('Instrument', {})
                symbol = instrument.get('Symbol', '')
                uic = instrument.get('Uic')
                asset_type = instrument.get('AssetType', 'Stock')
                
                # Nettoyer le symbole (enlever l'échange si présent, ex: "MP:xnys" -> "MP")
                if symbol and ':' in symbol:
                    symbol = symbol.split(':')[0]
                
                # Si pas de symbole, essayer de le récupérer depuis l'UIC
                if not symbol and uic:
                    try:
                        symbol = self._get_symbol_from_uic(uic, asset_type)
                        if not symbol:
                            symbol = f"UIC_{uic}"
                    except:
                        symbol = f"UIC_{uic}" if uic else 'UNKNOWN'
                elif not symbol:
                    symbol = 'UNKNOWN'
                
                # Filtrer par symbole si spécifié
                if symbol_filter and symbol != symbol_filter:
                    continue
                
                # Extraire les frais depuis Bookings
                total_fees = Decimal('0')
                bookings = txn.get('Bookings', [])
                for booking in bookings:
                    amount_type = booking.get('AmountType', '')
                    if amount_type == 'Commission':
                        booked_amount = Decimal(str(booking.get('BookedAmount', 0)))
                        total_fees += abs(booked_amount)  # Frais en valeur absolue
                
                # Parcourir chaque trade dans le tableau Trades[]
                for trade_item in trades_array:
                    to_open_or_close = trade_item.get('ToOpenOrClose', '')
                    if not to_open_or_close or to_open_or_close not in ['ToOpen', 'ToClose']:
                        continue
                    
                    # Extraire les données du trade
                    trade_id = str(trade_item.get('TradeId', ''))
                    if not trade_id:
                        trade_id = str(txn.get('TradeId', ''))
                    
                    traded_quantity = Decimal(str(trade_item.get('TradedQuantity', 0)))
                    price = Decimal(str(trade_item.get('Price', 0)))
                    trade_execution_time = trade_item.get('TradeExecutionTime')
                    
                    # Utiliser la date du trade ou de la transaction
                    executed_at = trade_execution_time or txn.get('Date')
                    if executed_at and 'T' not in str(executed_at):
                        # Si seulement une date, ajouter une heure par défaut
                        executed_at = f"{executed_at}T00:00:00Z"
                    
                    # Déterminer le trade_type
                    trade_event_type = trade_item.get('TradeEventType', '')
                    event = txn.get('Event', '')
                    
                    if trade_event_type in ['Bought', 'BoughtOddLot'] or event == 'Buy':
                        trade_type = 'BUY'
                    elif trade_event_type in ['Sold', 'SoldOddLot'] or event == 'Sell':
                        trade_type = 'SELL'
                    elif to_open_or_close == 'ToOpen':
                        # Pour l'ouverture, on détermine selon TradedValue
                        # Si TradedValue est négatif, c'est un achat (débit)
                        traded_value = Decimal(str(trade_item.get('TradedValue', 0)))
                        trade_type = 'BUY' if traded_value < 0 else 'SELL'
                    else:  # ToClose
                        trade_type = 'SELL' if traded_quantity > 0 else 'BUY'
                    
                    # Créer un identifiant unique pour ce trade
                    position_id = str(trade_item.get('PositionId', ''))
                    order_id = str(trade_item.get('OrderId', ''))
                    
                    # ID composite pour éviter les doublons
                    if trade_id and order_id:
                        broker_trade_id = f"{trade_id}_{order_id}"
                    elif trade_id:
                        broker_trade_id = f"{trade_id}_{position_id}" if position_id else trade_id
                    else:
                        broker_trade_id = f"TX_{position_id}" if position_id else f"TX_{len(trades)}"
                    
                    # Éviter les doublons
                    if broker_trade_id in seen_trade_ids:
                        continue
                    seen_trade_ids.add(broker_trade_id)
                    
                    # Créer le BrokerTrade
                    trade = BrokerTrade(
                        symbol=symbol,
                        trade_type=trade_type,
                        quantity=abs(traded_quantity),  # Quantité absolue
                        price=price,
                        executed_at=executed_at,
                        broker_trade_id=broker_trade_id,
                        fees=total_fees,
                        raw_data={
                            'uic': uic,
                            'asset_type': asset_type,
                            'to_open_or_close': to_open_or_close,
                            'trade_id': trade_id,
                            'position_id': position_id,
                            'order_id': order_id,
                            'traded_value': float(trade_item.get('TradedValue', 0)),
                            'trade_event_type': trade_event_type,
                            'venue': trade_item.get('Venue'),
                            'exchange': trade_item.get('ExchangeName'),
                        }
                    )
                    trades.append(trade)
                    
                    # Limiter le nombre de trades retournés
                    if len(trades) >= limit:
                        break
                    
                # Si on a atteint la limite, sortir aussi de la boucle principale
                if len(trades) >= limit:
                    break
            
            logger.info(f"Saxo: Retrieved {len(trades)} trades from {len(transactions)} transactions")
            return trades
            
        except BrokerError:
            raise
        except Exception as e:
            logger.error(f"Saxo get_trades error: {e}")
            raise BrokerAPIError(f"Failed to get trades: {e}")
    
    # ==================== Orders ====================
    
    def get_orders(self, status: str = None, limit: int = 50) -> List[BrokerOrder]:
        """
        Récupérer les ordres
        
        Args:
            status: Filtrer par statut (optionnel)
            limit: Nombre maximum d'ordres
            
        Returns:
            Liste de BrokerOrder
        """
        try:
            params = {
                "$top": limit,
            }
            if self.client_key:
                params['ClientKey'] = self.client_key
            if status:
                params['Status'] = status
            
            data = self._make_request('GET', '/port/v1/orders', params=params)
            
            orders = []
            for item in data.get('Data', []):
                order = BrokerOrder(
                    symbol=item.get('Symbol', ''),
                    side='buy' if item.get('BuySell') == 'Buy' else 'sell',
                    quantity=Decimal(str(item.get('Amount', 0))),
                    price=Decimal(str(item.get('Price', 0))) if item.get('Price') else None,
                    order_type=item.get('OrderType', 'Market'),
                    status=item.get('Status', 'Unknown'),
                    broker_order_id=str(item.get('OrderId', '')),
                    filled_quantity=Decimal(str(item.get('FilledAmount', 0))),
                    created_at=item.get('OrderTime'),
                    raw_data={
                        'uic': item.get('Uic'),
                        'asset_type': item.get('AssetType'),
                        'duration': item.get('Duration', {}),
                        'account_id': item.get('AccountId'),
                    }
                )
                orders.append(order)
            
            return orders
            
        except BrokerError:
            raise
        except Exception as e:
            logger.error(f"Saxo get_orders error: {e}")
            raise BrokerAPIError(f"Failed to get orders: {e}")
    
    def place_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: Decimal, 
        price: Optional[Decimal] = None,
        order_type: str = None,
        uic: int = None,
        asset_type: str = "Stock",
        **kwargs
    ) -> OrderResult:
        """
        Placer un ordre
        
        Args:
            symbol: Symbole de l'asset
            side: 'buy' ou 'sell'
            quantity: Quantité à acheter/vendre
            price: Prix limite (optionnel, market si None)
            order_type: Type d'ordre (Market, Limit, Stop, etc.)
            uic: UIC Saxo de l'asset
            asset_type: Type d'asset
            
        Returns:
            OrderResult avec le résultat de l'ordre
        """
        try:
            # Obtenir l'UIC si non fourni
            if uic is None:
                uic = self._get_uic_from_symbol(symbol, asset_type)
                if uic is None:
                    return OrderResult(
                        success=False,
                        error_message=f"Could not find UIC for {symbol}"
                    )
            
            # Déterminer le type d'ordre
            if order_type is None:
                order_type = 'Limit' if price else 'Market'
            
            # Mapper le type d'asset
            saxo_asset_type = self.ASSET_TYPE_MAPPING.get(
                asset_type.lower(), 
                asset_type
            )
            
            # Construire les données de l'ordre
            order_data = {
                "Uic": uic,
                "AssetType": saxo_asset_type,
                "Amount": float(quantity),
                "BuySell": "Buy" if side.lower() == 'buy' else "Sell",
                "OrderType": order_type,
            }
            
            # Ajouter le compte si disponible
            if self.account_key:
                order_data["AccountKey"] = self.account_key
            
            # Ajouter le prix pour les ordres limite
            if price and order_type in ['Limit', 'StopLimit']:
                order_data["OrderPrice"] = float(price)
            
            # Durée de l'ordre
            duration = kwargs.get('duration', 'DayOrder')
            order_data["OrderDuration"] = {"DurationType": duration}
            
            # Placer l'ordre
            data = self._make_request('POST', '/trade/v2/orders', json_data=order_data)
            
            order_id = data.get('OrderId')
            
            logger.info(f"Saxo: Order placed - ID: {order_id}, {side} {quantity} {symbol}")
            
            return OrderResult(
                success=True,
                order_id=str(order_id) if order_id else None,
                broker_order_id=str(order_id) if order_id else None,
                status=data.get('Status', 'Submitted'),
                filled_quantity=Decimal('0'),
                raw_data=data
            )
            
        except BrokerError as e:
            logger.error(f"Saxo place_order broker error: {e}")
            return OrderResult(
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Saxo place_order error: {e}")
            return OrderResult(
                success=False,
                error_message=f"Order placement failed: {e}"
            )
    
    def cancel_order(self, order_id: str, **kwargs) -> bool:
        """
        Annuler un ordre
        
        Args:
            order_id: ID de l'ordre à annuler
            
        Returns:
            True si l'annulation a réussi
        """
        try:
            params = {}
            if self.account_key:
                params['AccountKey'] = self.account_key
            
            self._make_request(
                'DELETE', 
                f'/trade/v2/orders/{order_id}',
                params=params
            )
            
            logger.info(f"Saxo: Order {order_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Saxo cancel_order error: {e}")
            return False
    
    def modify_order(
        self, 
        order_id: str, 
        quantity: Decimal = None, 
        price: Decimal = None,
        **kwargs
    ) -> bool:
        """
        Modifier un ordre existant
        
        Args:
            order_id: ID de l'ordre à modifier
            quantity: Nouvelle quantité (optionnel)
            price: Nouveau prix (optionnel)
            
        Returns:
            True si la modification a réussi
        """
        try:
            # Récupérer l'ordre actuel
            orders = self.get_orders()
            current_order = None
            for order in orders:
                if order.broker_order_id == order_id:
                    current_order = order
                    break
            
            if not current_order:
                logger.error(f"Saxo: Order {order_id} not found")
                return False
            
            # Construire les données de modification
            modify_data = {
                "OrderId": order_id,
            }
            
            if self.account_key:
                modify_data["AccountKey"] = self.account_key
            
            if quantity is not None:
                modify_data["Amount"] = float(quantity)
            
            if price is not None:
                modify_data["OrderPrice"] = float(price)
            
            self._make_request('PATCH', f'/trade/v2/orders/{order_id}', json_data=modify_data)
            
            logger.info(f"Saxo: Order {order_id} modified")
            return True
            
        except Exception as e:
            logger.error(f"Saxo modify_order error: {e}")
            return False
    
    # ==================== Account ====================
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Récupérer les informations du compte
        
        Returns:
            Dictionnaire avec les informations du compte
        """
        try:
            # D'abord récupérer les comptes pour obtenir l'AccountKey
            account_params = {}
            if self.client_key:
                account_params['ClientKey'] = self.client_key
            
            account_data = self._make_request('GET', '/port/v1/accounts', params=account_params)
            
            accounts = account_data.get('Data', [])
            if not accounts:
                logger.warning("No accounts found in Saxo response")
                return {}
            
            primary_account = accounts[0]
            account_key = primary_account.get('AccountKey')
            # Le ClientKey est aussi dans la réponse du compte
            client_key_from_account = primary_account.get('ClientKey')
            
            # Utiliser le ClientKey de la réponse si disponible, sinon celui des credentials
            client_key_to_use = client_key_from_account or self.client_key
            
            # Maintenant récupérer les balances avec l'AccountKey ET ClientKey (les deux sont requis)
            balance_params = {}
            if account_key:
                balance_params['AccountKey'] = account_key
            if client_key_to_use:
                balance_params['ClientKey'] = client_key_to_use
            
            # Les deux sont requis par l'API Saxo
            if not balance_params.get('AccountKey') or not balance_params.get('ClientKey'):
                logger.warning(f"Missing required parameters for balances: AccountKey={bool(account_key)}, ClientKey={bool(self.client_key)}")
                # Essayer quand même, mais cela échouera probablement
            
            balance_data = self._make_request('GET', '/port/v1/balances', params=balance_params)
            
            # Si balance_data est une liste, prendre le premier élément
            if isinstance(balance_data, list) and balance_data:
                balance_data = balance_data[0]
            elif isinstance(balance_data, dict) and 'Data' in balance_data:
                balance_data = balance_data['Data'][0] if balance_data['Data'] else {}
            
            return {
                'account_id': primary_account.get('AccountId'),
                'account_key': account_key,
                'currency': primary_account.get('Currency', 'EUR'),
                'balance': balance_data.get('TotalValue', 0) if isinstance(balance_data, dict) else 0,
                'cash_balance': balance_data.get('CashBalance', 0) if isinstance(balance_data, dict) else 0,
                'margin_available': balance_data.get('MarginAvailableForTrading', 0) if isinstance(balance_data, dict) else 0,
                'margin_used': balance_data.get('MarginUsedByCurrentPositions', 0) if isinstance(balance_data, dict) else 0,
                'unrealized_pnl': balance_data.get('UnrealizedProfitLoss', 0) if isinstance(balance_data, dict) else 0,
                'account_type': primary_account.get('AccountType'),
                'is_active': primary_account.get('Active', False),
            }
            
        except Exception as e:
            logger.error(f"Saxo get_account_info error: {e}", exc_info=True)
            return {}
    
    def get_account_balance(self) -> Dict[str, Decimal]:
        """
        Get account balances.
        
        Returns:
            Dictionary mapping currency to balance
        """
        try:
            # Récupérer les informations du compte
            account_info = self.get_account_info()
            
            if not account_info:
                return {}
            
            # Extraire la devise et le solde
            currency = account_info.get('currency', 'EUR')
            cash_balance = account_info.get('cash_balance', 0)
            total_balance = account_info.get('balance', 0)
            
            # Formater les balances
            balances = {}
            
            # Solde en cash (devise principale)
            if cash_balance:
                balances[currency] = Decimal(str(cash_balance))
            
            # Solde total (si différent)
            if total_balance and total_balance != cash_balance:
                balances[f'{currency}_total'] = Decimal(str(total_balance))
            
            # Autres informations
            if account_info.get('margin_available'):
                balances[f'{currency}_margin_available'] = Decimal(str(account_info['margin_available']))
            
            return balances
            
        except Exception as e:
            logger.error(f"Saxo get_account_balance error: {e}")
            self._set_error(f"Get account balance error: {str(e)}")
            return {}
    
    # ==================== Helper Methods ====================
    
    def _get_uic_from_symbol(
        self, 
        symbol: str, 
        asset_type: str = "Stock"
    ) -> Optional[int]:
        """
        Récupérer l'UIC depuis le symbole
        
        Args:
            symbol: Symbole de l'asset
            asset_type: Type d'asset
            
        Returns:
            UIC ou None
        """
        try:
            assets = self.get_assets(
                asset_type=asset_type,
                keywords=symbol,
                limit=10
            )
            
            for asset in assets:
                if asset.symbol.upper() == symbol.upper():
                    return asset.raw_data.get('uic') if asset.raw_data else None
            
            # Si pas de correspondance exacte, prendre le premier
            if assets:
                return assets[0].raw_data.get('uic') if assets[0].raw_data else None
            
            return None
            
        except Exception as e:
            logger.error(f"Saxo _get_uic_from_symbol error: {e}")
            return None
    
    def _get_symbol_from_uic(
        self, 
        uic: int, 
        asset_type: str = "Stock"
    ) -> Optional[str]:
        """
        Récupérer le symbole depuis l'UIC
        
        Args:
            uic: UIC de l'asset
            asset_type: Type d'asset
            
        Returns:
            Symbole de l'asset ou None
        """
        try:
            if not uic:
                return None
            
            # Mapper le type d'asset
            saxo_asset_type = self.ASSET_TYPE_MAPPING.get(
                asset_type.lower(), 
                asset_type
            )
            
            # L'API Saxo /ref/v1/instruments ne supporte pas directement la recherche par UIC
            # On utilise plutôt l'endpoint /trade/v1/infoprices qui retourne des infos incluant parfois le symbole
            # Ou on peut chercher dans un cache si disponible
            # Pour l'instant, on essaie d'utiliser l'endpoint infoprices qui peut contenir des métadonnées
            
            params = {
                "Uic": uic,
                "AssetType": saxo_asset_type,
            }
            
            try:
                # L'endpoint infoprices peut ne pas retourner le symbole directement
                # Mais on peut essayer de le trouver via une recherche large puis filtrer par UIC
                # Pour l'instant, on retourne None et on laisse le fallback gérer
                # (Cela évite de faire trop de requêtes API)
                logger.debug(f"Saxo: Attempting to find symbol for UIC {uic}")
                return None  # Retourner None pour utiliser le fallback
                
            except Exception as e:
                logger.debug(f"Saxo: Could not retrieve symbol for UIC {uic}: {e}")
                return None
            
        except Exception as e:
            logger.warning(f"Saxo _get_symbol_from_uic error for UIC {uic}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Tester la connexion au broker
        
        Returns:
            True si la connexion est fonctionnelle
        """
        try:
            if not self.authenticate():
                return False
            
            # Faire une requête simple pour vérifier
            self._make_request('GET', '/port/v1/accounts')
            return True
            
        except Exception as e:
            logger.error(f"Saxo test_connection error: {e}")
            return False

