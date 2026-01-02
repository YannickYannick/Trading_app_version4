"""
Position Synchronization Service.

This service synchronizes positions from brokers to the local database.

Flux de synchronisation pour les positions Saxo:
------------------------------------------------

1. Récupération des positions depuis l'API Saxo via SaxoBroker.get_positions()
2. Pour chaque position, création/matching d'un AllAsset intelligent:
   - Étape 1: Recherche par (symbol, platform)
   - Étape 2: Si symbol = "UIC_xxxx", recherche par saxo_uic
   - Étape 3: Récupération depuis API Saxo via /instruments/details/{UIC}/{AssetType}
     → Utilise l'endpoint rapide pour récupérer les vraies données (symbol, name, etc.)
   - Étape 4: Création minimale en fallback si tout échoue
3. Création/mise à jour de la Position avec le bon AllAsset

Documentation complète: docs/saxo_position_sync_flow.md
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .base_sync_service import BaseSyncService
from ...brokers.factory import BrokerFactory
from ...brokers.base import BrokerPosition, BrokerBase
from ...models import BrokerAccount, Position, Asset, AllAssets, Broker
from ...exceptions import SyncException, SyncAuthenticationError

logger = logging.getLogger('trading.services.sync.positions')


class PositionSyncService(BaseSyncService):
    """
    Service for synchronizing positions from brokers.
    
    Features:
    - Sync positions from any supported broker
    - Create/update local Position records
    - Close positions that no longer exist on broker
    - Calculate P&L for synced positions
    
    Usage:
        service = PositionSyncService(user)
        result = service.sync(broker_account)
    """
    
    SYNC_TYPE = 'positions'
    
    def sync(
        self,
        broker_account: BrokerAccount,
        close_missing: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync positions from a broker.
        
        Args:
            broker_account: BrokerAccount to sync from
            close_missing: Whether to close positions not found on broker
            **kwargs: Additional parameters
            
        Returns:
            Dict with sync results
        """
        self._log_start(
            f"Starting position sync for {broker_account.broker.name}",
            broker=broker_account.broker.name
        )
        
        try:
            # Get broker instance
            credentials = self._get_credentials(broker_account)
            broker_type = broker_account.get_broker_type()
            broker = BrokerFactory.create_broker(broker_type, self.user, credentials)
            
            # Authenticate
            if not broker.authenticate():
                raise SyncAuthenticationError(
                    sync_type=self.SYNC_TYPE,
                    broker_type=broker_type,
                )
            
            # Fetch positions from broker
            broker_positions = broker.get_positions()
            
            self.logger.info(
                f"Retrieved {len(broker_positions)} positions from {broker_type}"
            )
            
            # Sync positions to database
            with transaction.atomic():
                result = self._sync_positions(
                    broker_account=broker_account,
                    broker_positions=broker_positions,
                    close_missing=close_missing,
                )
            
            # Log completion
            self._log_complete(
                created=result.get('created', 0),
                updated=result.get('updated', 0),
                broker=broker_account.broker.name
            )
            
            # Create sync log
            self._create_sync_log(
                broker_account=broker_account,
                status='success' if not self._errors else 'partial',
                records_synced=result.get('created', 0) + result.get('updated', 0),
                details=result,
            )
            
            return result
            
        except SyncException:
            raise
        except Exception as e:
            self._log_error("Position sync failed", error=e)
            
            self._create_sync_log(
                broker_account=broker_account,
                status='error',
                error_message=str(e),
            )
            
            raise SyncException(
                message=f"Position sync failed: {str(e)}",
                sync_type=self.SYNC_TYPE,
            )
    
    def _sync_positions(
        self,
        broker_account: BrokerAccount,
        broker_positions: List[BrokerPosition],
        close_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Sync positions to database.
        
        Args:
            broker_account: BrokerAccount being synced
            broker_positions: List of positions from broker
            close_missing: Whether to close missing positions
            
        Returns:
            Dict with sync statistics
        """
        created = 0
        updated = 0
        closed = 0
        
        # Track which positions we've seen
        seen_position_ids = set()
        
        for broker_pos in broker_positions:
            try:
                self.logger.debug(
                    f"Processing position: {broker_pos.symbol}, "
                    f"side={broker_pos.side}, quantity={broker_pos.quantity}"
                )
                
                result = self._sync_single_position(
                    broker_account=broker_account,
                    broker_position=broker_pos,
                )
                
                if result.get('created'):
                    created += 1
                    self.logger.info(f"Created position for {broker_pos.symbol}")
                elif result.get('updated'):
                    updated += 1
                    self.logger.info(f"Updated position for {broker_pos.symbol}")
                
                if result.get('position_id'):
                    seen_position_ids.add(result['position_id'])
                    
            except Exception as e:
                error_msg = f"Failed to sync position {broker_pos.symbol}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                self._log_error(
                    f"Failed to sync position {broker_pos.symbol}",
                    error=e,
                    symbol=broker_pos.symbol
                )
        
        # Close positions that no longer exist on broker
        if close_missing:
            closed = self._close_missing_positions(
                broker_account=broker_account,
                seen_position_ids=seen_position_ids,
            )
        
        return self._build_result(
            success=len(self._errors) == 0,
            created=created,
            updated=updated,
            deleted=closed,
            closed=closed,
        )
    
    def _sync_single_position(
        self,
        broker_account: BrokerAccount,
        broker_position: BrokerPosition,
    ) -> Dict[str, Any]:
        """
        Sync a single position.
        
        Args:
            broker_account: BrokerAccount being synced
            broker_position: Position data from broker
            
        Returns:
            Dict with result info
        """
        # Validate symbol
        if not broker_position.symbol or not broker_position.symbol.strip():
            error_msg = f"Position has empty or invalid symbol"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Find or create AllAsset (source de vérité unique)
        try:
            # Extraire l'UIC et l'asset_type depuis raw_data si disponible
            raw_data = broker_position.raw_data or {}
            uic_raw = raw_data.get('uic')
            asset_type = raw_data.get('asset_type')
            
            # Convertir l'UIC en int de manière robuste
            uic = None
            if uic_raw is not None:
                try:
                    uic = int(uic_raw)
                except (ValueError, TypeError):
                    self.logger.warning(
                        f"Invalid UIC value '{uic_raw}' for position {broker_position.symbol}, "
                        f"skipping UIC-based lookup"
                    )
                    uic = None
            
            # Logger pour débugger les positions avec UIC fallback
            if broker_position.symbol.startswith('UIC_'):
                self.logger.info(
                    f"Position with UIC fallback symbol: {broker_position.symbol}, "
                    f"UIC={uic}, asset_type={asset_type}, "
                    f"will attempt to fetch real symbol from API"
                )
            
            # Récupérer l'instance du broker pour pouvoir appeler get_asset_by_uic si nécessaire
            broker_instance = None
            if broker_account.get_broker_type() == 'SAXO' and uic:
                try:
                    credentials = self._get_credentials(broker_account)
                    broker_instance = BrokerFactory.create_broker(
                        broker_account.get_broker_type(),
                        self.user,
                        credentials
                    )
                    # S'assurer que le broker est authentifié
                    if not broker_instance.is_connected:
                        if not broker_instance.authenticate():
                            self.logger.error(
                                f"Failed to authenticate Saxo broker for UIC lookup. "
                                f"Position will use fallback symbol."
                            )
                            broker_instance = None
                except Exception as e:
                    self.logger.error(
                        f"Error creating broker instance for UIC lookup: {e}",
                        exc_info=True
                    )
                    broker_instance = None
            
            all_asset = self._get_or_create_all_asset(
                symbol=broker_position.symbol,
                broker_type=broker_account.get_broker_type(),
                uic=uic,
                asset_type=asset_type,
                broker_instance=broker_instance,
            )
        except Exception as e:
            error_msg = f"Error getting/creating AllAsset for {broker_position.symbol}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
        
        if not all_asset:
            error_msg = f"Could not find or create AllAsset: {broker_position.symbol}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.debug(
            f"Syncing position {broker_position.symbol}: "
            f"all_asset_id={all_asset.id}, side={broker_position.side}, "
            f"quantity={broker_position.quantity}"
        )
        
        # Determine broker position ID
        broker_position_id = broker_position.broker_position_id or f"{broker_account.get_broker_type()}_{broker_position.symbol}"
        
        # Convert side: BrokerPosition uses 'LONG'/'SHORT', Position model also uses 'LONG'/'SHORT'
        # So we can use it directly, but ensure it's uppercase
        side = broker_position.side.upper() if broker_position.side else 'LONG'
        if side not in ['LONG', 'SHORT']:
            # Fallback: if side is invalid, determine from quantity
            side = 'LONG' if broker_position.quantity >= 0 else 'SHORT'
        
        # For Binance spot positions, entry_price might be 0
        # Use current_price as entry_price if entry_price is 0 (for spot balances)
        entry_price = broker_position.entry_price
        if entry_price == 0 and broker_position.current_price > 0:
            entry_price = broker_position.current_price
        
        # Try to find existing open position first
        # Look for open position with same user, broker, all_asset, and side
        existing_position = Position.objects.filter(
            user=self.user,
            broker=broker_account.broker,
            all_asset=all_asset,
            side=side,
            is_open=True,
        ).first()
        
        if existing_position:
            # Update existing position
            self.logger.info(f"Updating existing position {existing_position.id} for {broker_position.symbol} (side={side})")
            existing_position.quantity = broker_position.quantity
            existing_position.entry_price = entry_price
            existing_position.current_price = broker_position.current_price
            existing_position.side = side  # Ensure side is correct
            existing_position.is_open = True  # Ensure it's open
            existing_position.save()
            created = False
            position = existing_position
            symbol = position.all_asset.symbol if position.all_asset else 'Unknown'
            self.logger.info(f"Position {position.id} updated successfully: {symbol} {position.side} qty={position.quantity}")
        else:
            # Create new position
            self.logger.info(f"Creating new position for {broker_position.symbol} (side={side}, qty={broker_position.quantity})")
            try:
                position = Position.objects.create(
                    user=self.user,
                    broker=broker_account.broker,
                    all_asset=all_asset,  # Utiliser AllAssets directement
                    side=side,
                    quantity=broker_position.quantity,
                    entry_price=entry_price,
                    current_price=broker_position.current_price,
                    is_open=True,
                )
                created = True
                symbol = position.all_asset.symbol if position.all_asset else 'Unknown'
                self.logger.info(f"Position {position.id} created successfully: {symbol} {position.side} qty={position.quantity}")
            except Exception as e:
                self.logger.error(
                    f"Failed to create position for {broker_position.symbol}: {str(e)}",
                    exc_info=True
                )
                raise
        
        return {
            'created': created,
            'updated': not created,
            'position_id': position.id,
        }
    
    def _close_missing_positions(
        self,
        broker_account: BrokerAccount,
        seen_position_ids: set,
    ) -> int:
        """
        Close positions that no longer exist on broker.
        
        Args:
            broker_account: BrokerAccount being synced
            seen_position_ids: Set of position IDs that still exist
            
        Returns:
            Number of positions closed
        """
        # Get open positions for this broker account
        open_positions = Position.objects.filter(
            user=self.user,
            broker=broker_account.broker,
            is_open=True,
        ).exclude(id__in=seen_position_ids)
        
        count = open_positions.count()
        
        if count > 0:
            # Mark as closed
            open_positions.update(
                is_open=False,
                closed_at=timezone.now(),
            )
            
            self._log_warning(
                f"Closed {count} positions not found on broker",
                count=count
            )
        
        return count
    
    def _get_or_create_all_asset(
        self,
        symbol: str,
        broker_type: str,
        uic: Optional[int] = None,
        asset_type: Optional[str] = None,
        broker_instance: Optional[BrokerBase] = None,
    ) -> Optional[AllAssets]:
        """
        Get or create an AllAsset for the given symbol.
        
        AllAssets est la source de vérité unique. Si l'asset n'existe pas,
        on essaie de le récupérer depuis l'API du broker (si UIC disponible)
        avant de créer un AllAsset minimal.
        
        Args:
            symbol: Asset symbol (peut être "UIC_xxxx" si symbole réel non disponible)
            broker_type: Type of broker (SAXO, BINANCE, etc.)
            uic: UIC de l'asset (optionnel, pour Saxo)
            asset_type: Type d'asset (optionnel, pour améliorer la recherche)
            broker_instance: Instance du broker (optionnel, pour appeler l'API)
            
        Returns:
            AllAssets instance or None
        """
        platform = broker_type.upper()
        
        # 1. Chercher dans AllAssets avec (symbol, platform) unique
        all_asset = AllAssets.objects.filter(
            symbol=symbol,
            platform=platform,
        ).first()
        
        if all_asset:
            # Si l'AllAsset existe mais n'a pas d'UIC alors qu'on en a un, le mettre à jour
            if platform == 'SAXO' and uic and not all_asset.saxo_uic:
                all_asset.saxo_uic = uic
                all_asset.save(update_fields=['saxo_uic'])
                self.logger.debug(f"Updated saxo_uic for {symbol}: {uic}")
            return all_asset
        
        # 2. Si symbol = "UIC_xxxx" et UIC disponible, chercher par UIC
        if symbol.startswith('UIC_') and uic:
            try:
                # Convertir l'UIC du symbol en int pour comparaison
                extracted_uic = int(symbol.replace('UIC_', ''))
                
                # S'assurer que uic est aussi un int
                uic_int = int(uic) if not isinstance(uic, int) else uic
                
                if extracted_uic == uic_int:
                    # Chercher par saxo_uic
                    all_asset = AllAssets.objects.filter(
                        saxo_uic=uic_int,
                        platform=platform,
                    ).first()
                    
                    if all_asset:
                        self.logger.info(
                            f"Found AllAsset by UIC {uic_int}: {all_asset.symbol} "
                            f"(was looking for {symbol})"
                        )
                        return all_asset
                    else:
                        self.logger.debug(
                            f"No existing AllAsset found with saxo_uic={uic_int}, "
                            f"will try to fetch from API"
                        )
            except (ValueError, TypeError) as e:
                self.logger.warning(
                    f"Error extracting UIC from symbol {symbol}: {e}"
                )
        
        # 3. Si toujours pas trouvé et UIC disponible, essayer de récupérer depuis l'API
        if platform == 'SAXO' and uic and broker_instance:
            try:
                from ...brokers.saxo import SaxoBroker
                if isinstance(broker_instance, SaxoBroker):
                    # S'assurer que uic est un int
                    uic_int = int(uic) if not isinstance(uic, int) else uic
                    
                    self.logger.info(
                        f"Attempting to fetch asset from Saxo API for UIC {uic_int} "
                        f"(asset_type={asset_type or 'Stock'})"
                    )
                    
                    broker_asset = broker_instance.get_asset_by_uic(
                        uic=uic_int,
                        asset_type=asset_type or 'Stock'
                    )
                    
                    if broker_asset:
                        self.logger.info(
                            f"✅ Successfully fetched asset from API: {broker_asset.symbol} "
                            f"({broker_asset.name}) for UIC {uic_int}"
                        )
                        # Créer AllAsset avec toutes les données disponibles
                        raw_data = broker_asset.raw_data or {}
                        all_asset = AllAssets.objects.create(
                            symbol=broker_asset.symbol,  # Le vrai symbole, pas "UIC_xxxx"
                            name=broker_asset.name,
                            platform=platform,
                            asset_type=broker_asset.asset_type or asset_type or 'UNKNOWN',
                            market=raw_data.get('country_code', ''),
                            currency=broker_asset.currency or 'USD',
                            exchange=broker_asset.exchange or raw_data.get('exchange_id', ''),
                            is_tradable=broker_asset.is_tradable,
                            # Champs spécifiques Saxo
                            saxo_uic=uic_int,
                            saxo_exchange_id=raw_data.get('exchange_id', ''),
                            saxo_country_code=raw_data.get('country_code', ''),
                        )
                        self.logger.info(
                            f"Created AllAsset from API for UIC {uic_int}: "
                            f"{broker_asset.symbol} ({broker_asset.name})"
                        )
                        return all_asset
                    else:
                        self.logger.warning(
                            f"⚠️ get_asset_by_uic returned None for UIC {uic_int}. "
                            f"Asset may not be found in API or search limit reached."
                        )
            except Exception as e:
                self.logger.error(
                    f"❌ Exception while fetching asset from API for UIC {uic}: {e}",
                    exc_info=True
                )
        
        # 4. Si pas trouvé, créer un AllAsset minimal
        # L'utilisateur devra lancer une sync AllAssets pour enrichir les données
        self.logger.warning(
            f"AllAsset not found for {symbol} ({platform}). "
            f"Creating minimal AllAsset. Consider running asset sync first."
        )
        
        try:
            create_kwargs = {
                'symbol': symbol,
                'name': symbol,  # Nom par défaut = symbol
                'platform': platform,
                'asset_type': asset_type or 'UNKNOWN',
                'market': '',
                'currency': 'USD',
                'is_tradable': True,
            }
            
            # Ajouter l'UIC si disponible (même si symbol = "UIC_xxxx")
            if platform == 'SAXO' and uic:
                create_kwargs['saxo_uic'] = uic
            
            all_asset = AllAssets.objects.create(**create_kwargs)
            self.logger.info(f"Created minimal AllAsset for {symbol} ({platform})")
            return all_asset
        except Exception as e:
            self.logger.error(
                f"Failed to create AllAsset for {symbol} ({platform}): {str(e)}",
                exc_info=True
            )
            return None
    
    def _get_credentials(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """
        Get credentials from broker account.
        Utilise la méthode get_credentials_dict() du modèle.
        """
        # Utiliser la méthode du modèle qui gère déjà tout
        credentials = broker_account.get_credentials_dict()
        
        # Ajouter des informations supplémentaires si nécessaire
        credentials['user_id'] = broker_account.user.id
        if broker_account.account_id:
            credentials['account_id'] = broker_account.account_id
        
        return credentials
    
    def sync_for_all_accounts(self) -> Dict[str, Any]:
        """
        Sync positions for all user's broker accounts.
        
        Returns:
            Dict with aggregated results
        """
        accounts = BrokerAccount.objects.filter(
            user=self.user,
            is_active=True,
        )
        
        total_created = 0
        total_updated = 0
        total_closed = 0
        account_results = {}
        
        for account in accounts:
            try:
                result = self.sync(account)
                account_results[account.account_name or account.account_id] = result
                
                total_created += result.get('created', 0)
                total_updated += result.get('updated', 0)
                total_closed += result.get('closed', 0)
                
            except Exception as e:
                self._log_error(
                    f"Failed to sync account {account.account_id}",
                    error=e
                )
                account_results[account.account_name or account.account_id] = {
                    'success': False,
                    'error': str(e),
                }
        
        return {
            'success': len(self._errors) == 0,
            'total_created': total_created,
            'total_updated': total_updated,
            'total_closed': total_closed,
            'accounts': len(accounts),
            'results': account_results,
        }

