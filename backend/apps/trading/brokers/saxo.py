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
from urllib.parse import urlencode

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
        'cfdonstock': 'CfdOnStock',
        'cfdonindex': 'CfdOnIndex',
        'cfdonforex': 'CfdOnForex',
        'cfdonforward': 'CfdOnForward',
        'cfdonoption': 'CfdOnOption',
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
        self.redirect_uri = credentials.get('redirect_uri', 'http://localhost:8080/callback')
        
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
                if isinstance(self.token_expires_at, str):
                    expires_at = datetime.fromisoformat(self.token_expires_at.replace('Z', '+00:00'))
                else:
                    expires_at = self.token_expires_at
                
                # Ajouter une marge de 5 minutes
                if datetime.now(expires_at.tzinfo) >= expires_at - timedelta(minutes=5):
                    return False
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse token expiry: {e}")
                return False
        
        return True
    
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
            self.token_expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
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
            self.token_expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
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
        limit: int = 20,
        exchange_id: str = None,
        **kwargs
    ) -> List[BrokerAsset]:
        """
        Récupérer la liste des assets depuis Saxo
        
        Args:
            asset_type: Type d'asset (Stock, Etf, CfdOnStock, etc.)
            keywords: Mots-clés de recherche
            limit: Nombre maximum de résultats
            exchange_id: ID de la bourse (optionnel)
            
        Returns:
            Liste de BrokerAsset
        """
        try:
            # Mapper le type d'asset
            saxo_asset_type = self.ASSET_TYPE_MAPPING.get(
                asset_type.lower(), 
                asset_type
            )
            
            params = {
                "AssetTypes": saxo_asset_type,
                "$top": limit,
            }
            
            if keywords:
                params["Keywords"] = keywords
            
            if exchange_id:
                params["ExchangeId"] = exchange_id
            
            data = self._make_request('GET', '/ref/v1/instruments', params=params)
            
            assets = []
            for item in data.get('Data', []):
                asset = BrokerAsset(
                    symbol=item.get('Symbol', ''),
                    name=item.get('Description', ''),
                    asset_type=item.get('AssetType', asset_type),
                    exchange=item.get('ExchangeId', ''),
                    currency=item.get('CurrencyCode', 'USD'),
                    broker_id=str(item.get('Uic', '')),
                    is_tradable=item.get('IsTradable', True),
                    extra_data={
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
            
            logger.info(f"Saxo: Retrieved {len(assets)} assets")
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
    
    def get_positions(self, **kwargs) -> List[BrokerPosition]:
        """
        Récupérer les positions ouvertes
        
        Returns:
            Liste de BrokerPosition
        """
        try:
            params = {}
            if self.client_key:
                params['ClientKey'] = self.client_key
            
            data = self._make_request('GET', '/port/v1/positions', params=params)
            
            positions = []
            for item in data.get('Data', []):
                position_base = item.get('PositionBase', {})
                position_view = item.get('PositionView', {})
                
                position = BrokerPosition(
                    symbol=position_base.get('Symbol', ''),
                    quantity=Decimal(str(position_base.get('Amount', 0))),
                    average_price=Decimal(str(position_view.get('AverageOpenPrice', 0))),
                    current_price=Decimal(str(position_view.get('CurrentPrice', 0))),
                    unrealized_pnl=Decimal(str(position_view.get('ProfitLossOnTrade', 0))),
                    currency=position_base.get('Currency', 'USD'),
                    broker_position_id=str(item.get('PositionId', '')),
                    extra_data={
                        'uic': position_base.get('Uic'),
                        'asset_type': position_base.get('AssetType'),
                        'account_id': position_base.get('AccountId'),
                        'status': position_base.get('Status'),
                        'execution_time': position_base.get('ExecutionTimeOpen'),
                        'value_date': position_base.get('ValueDate'),
                        'exposure': position_view.get('Exposure'),
                        'market_value': position_view.get('MarketValue'),
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
            
            return BrokerPosition(
                symbol=position_base.get('Symbol', ''),
                quantity=Decimal(str(position_base.get('Amount', 0))),
                average_price=Decimal(str(position_view.get('AverageOpenPrice', 0))),
                current_price=Decimal(str(position_view.get('CurrentPrice', 0))),
                unrealized_pnl=Decimal(str(position_view.get('ProfitLossOnTrade', 0))),
                currency=position_base.get('Currency', 'USD'),
                broker_position_id=str(data.get('PositionId', '')),
                extra_data={
                    'uic': position_base.get('Uic'),
                    'asset_type': position_base.get('AssetType'),
                }
            )
            
        except Exception as e:
            logger.error(f"Saxo get_position_details error: {e}")
            return None
    
    # ==================== Trades ====================
    
    def get_trades(self, limit: int = 50, **kwargs) -> List[BrokerTrade]:
        """
        Récupérer l'historique des trades
        
        Args:
            limit: Nombre maximum de trades à récupérer
            
        Returns:
            Liste de BrokerTrade
        """
        try:
            params = {
                "$top": limit,
            }
            if self.client_key:
                params['ClientKey'] = self.client_key
            
            # Récupérer les ordres exécutés
            data = self._make_request('GET', '/port/v1/orders', params=params)
            
            trades = []
            for item in data.get('Data', []):
                # Filtrer seulement les ordres exécutés
                status = item.get('Status', '')
                if status not in ['Filled', 'PartiallyFilled']:
                    continue
                
                trade = BrokerTrade(
                    symbol=item.get('Symbol', ''),
                    side='buy' if item.get('BuySell') == 'Buy' else 'sell',
                    quantity=Decimal(str(item.get('FilledAmount', item.get('Amount', 0)))),
                    price=Decimal(str(item.get('Price', 0))),
                    timestamp=item.get('FilledTime') or item.get('OrderTime'),
                    broker_trade_id=str(item.get('OrderId', '')),
                    commission=Decimal(str(item.get('Commission', 0))),
                    extra_data={
                        'uic': item.get('Uic'),
                        'asset_type': item.get('AssetType'),
                        'order_type': item.get('OrderType'),
                        'duration': item.get('Duration', {}).get('DurationType'),
                        'status': status,
                        'account_id': item.get('AccountId'),
                    }
                )
                trades.append(trade)
            
            logger.info(f"Saxo: Retrieved {len(trades)} trades")
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
                    extra_data={
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
                extra_data=data
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
            params = {}
            if self.client_key:
                params['ClientKey'] = self.client_key
            
            # Récupérer les balances
            balance_data = self._make_request('GET', '/port/v1/balances', params=params)
            
            # Récupérer les infos du compte
            account_data = self._make_request('GET', '/port/v1/accounts', params=params)
            
            accounts = account_data.get('Data', [])
            primary_account = accounts[0] if accounts else {}
            
            return {
                'account_id': primary_account.get('AccountId'),
                'account_key': primary_account.get('AccountKey'),
                'currency': primary_account.get('Currency', 'USD'),
                'balance': balance_data.get('TotalValue', 0),
                'cash_balance': balance_data.get('CashBalance', 0),
                'margin_available': balance_data.get('MarginAvailableForTrading', 0),
                'margin_used': balance_data.get('MarginUsedByCurrentPositions', 0),
                'unrealized_pnl': balance_data.get('UnrealizedProfitLoss', 0),
                'account_type': primary_account.get('AccountType'),
                'is_active': primary_account.get('Active', False),
            }
            
        except Exception as e:
            logger.error(f"Saxo get_account_info error: {e}")
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
                    return asset.extra_data.get('uic')
            
            # Si pas de correspondance exacte, prendre le premier
            if assets:
                return assets[0].extra_data.get('uic')
            
            return None
            
        except Exception as e:
            logger.error(f"Saxo _get_uic_from_symbol error: {e}")
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

