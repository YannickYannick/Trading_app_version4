"""
Asset Synchronization Service.

This service handles synchronization of assets from brokers
to the local AllAssets catalog.
"""
import logging
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from ...brokers.factory import BrokerFactory
from ...brokers.base import BrokerAsset
from ...models import BrokerAccount, BrokerSyncLog, AllAssets, Asset

logger = logging.getLogger('trading.services.sync.assets')


class AssetSyncService:
    """
    Service for synchronizing assets from brokers.
    
    This service fetches assets from broker APIs and stores them
    in the AllAssets catalog for universal asset lookup.
    
    Usage:
        service = AssetSyncService(user)
        result = service.sync_assets(broker_account, asset_type='Stock')
    """
    
    def __init__(self, user: User):
        """
        Initialize the asset sync service.
        
        Args:
            user: Django User instance
        """
        self.user = user
    
    @transaction.atomic
    def sync_assets(
        self,
        broker_account: BrokerAccount,
        asset_type: str = 'Stock',
        keywords: str = '',
        limit: int = 30000,
        update_existing: bool = True,
        batch_size: int = 500,
        incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Sync assets from a broker to the database.
        
        Args:
            broker_account: BrokerAccount model instance
            asset_type: Type of asset to sync
            keywords: Search keywords (optional)
            limit: Maximum number of assets to sync
            update_existing: Whether to update existing assets
            batch_size: Number of assets to process in each batch (for bulk operations)
            incremental: If True, only sync assets modified since last sync
            
        Returns:
            Dict with sync results including duration and statistics
        """
        start_time = time.time()
        sync_log = None
        
        try:
            # Get broker instance
            credentials = self._get_credentials(broker_account)
            broker_type = broker_account.get_broker_type()
            broker = BrokerFactory.create_broker(broker_type, self.user, credentials)
            
            # Authenticate with retry
            auth_success = self._authenticate_with_retry(broker, max_retries=2)
            if not auth_success:
                error_msg = broker.last_error or "Authentication failed"
                duration_ms = int((time.time() - start_time) * 1000)
                self._log_sync(broker_account, 'assets', 'error', error_message=error_msg)
                return {
                    'success': False,
                    'message': error_msg,
                    'created': 0,
                    'updated': 0,
                    'errors': [],
                    'duration_ms': duration_ms,
                }
            
            # Fetch assets from broker
            broker_assets = broker.get_assets(
                asset_type=asset_type,
                keywords=keywords,
                limit=limit
            )
            
            if not broker_assets:
                duration_ms = int((time.time() - start_time) * 1000)
                self._log_sync(
                    broker_account, 'assets', 'success',
                    details={'message': 'No assets found'}
                )
                return {
                    'success': True,
                    'message': 'No assets found in broker',
                    'created': 0,
                    'updated': 0,
                    'errors': [],
                    'duration_ms': duration_ms,
                }
            
            # Filter for incremental sync if requested
            if incremental:
                broker_assets = self._filter_incremental_assets(
                    broker_assets, broker_account, asset_type
                )
            
            # Process assets in batches using bulk operations
            platform = broker_account.get_broker_type().upper()
            result = self._process_assets_bulk(
                broker_assets, platform, update_existing, batch_size
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log the sync
            self._log_sync(
                broker_account, 'assets', 'success',
                records_synced=result['created'] + result['updated'],
                details={
                    'asset_type': asset_type,
                    'created': result['created'],
                    'updated': result['updated'],
                    'errors_count': len(result['errors']),
                    'duration_ms': duration_ms,
                    'total_processed': len(broker_assets),
                }
            )
            
            return {
                'success': True,
                'message': f'Synced {result["created"] + result["updated"]} assets ({result["created"]} created, {result["updated"]} updated)',
                'created': result['created'],
                'updated': result['updated'],
                'errors': result['errors'],
                'duration_ms': duration_ms,
                'total_processed': len(broker_assets),
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Error syncing assets: {e}")
            self._log_sync(broker_account, 'assets', 'error', error_message=str(e))
            return {
                'success': False,
                'message': str(e),
                'created': 0,
                'updated': 0,
                'errors': [{'error': str(e)}],
                'duration_ms': duration_ms,
            }
    
    def _process_assets_bulk(
        self,
        broker_assets: List[BrokerAsset],
        platform: str,
        update_existing: bool,
        batch_size: int = 500
    ) -> Dict[str, Any]:
        """
        Process assets in bulk using bulk_create and bulk_update for better performance.
        
        Args:
            broker_assets: List of BrokerAsset instances
            platform: Platform identifier
            update_existing: Whether to update if exists
            batch_size: Number of assets to process per batch
            
        Returns:
            Dict with created, updated counts and errors
        """
        created = 0
        updated = 0
        errors = []
        
        # Get all existing assets for this platform in one query
        symbols = [asset.symbol for asset in broker_assets]
        existing_assets = {
            (asset.symbol, asset.platform): asset
            for asset in AllAssets.objects.filter(
                symbol__in=symbols,
                platform=platform
            )
        }
        
        # Prepare assets for bulk operations
        assets_to_create = []
        assets_to_update = []
        
        for broker_asset in broker_assets:
            try:
                # Prepare defaults
                defaults = {
                    'name': broker_asset.name or '',
                    'asset_type': broker_asset.asset_type or '',
                    'exchange': broker_asset.exchange or '',
                    'currency': broker_asset.currency or 'USD',
                    'is_tradable': broker_asset.is_tradable if broker_asset.is_tradable is not None else True,
                    'symbole_yahoo': 'Not_searched',  # Initialiser pour validation Yahoo ultérieure
                }
                
                # Add broker-specific fields
                if platform == 'SAXO':
                    # Récupérer l'UIC depuis broker_id ou raw_data
                    uic_value = None
                    
                    # Essayer depuis broker_id d'abord
                    if broker_asset.broker_id and broker_asset.broker_id != 'None' and broker_asset.broker_id.strip():
                        try:
                            uic_value = int(broker_asset.broker_id)
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Could not convert broker_id to int for {broker_asset.symbol}: {broker_asset.broker_id} ({e})")
                    
                    # Fallback: vérifier dans raw_data (plus fiable car c'est la valeur brute de l'API)
                    if uic_value is None and hasattr(broker_asset, 'raw_data') and broker_asset.raw_data:
                        raw_uic = broker_asset.raw_data.get('uic')
                        if raw_uic is not None and raw_uic != '':
                            try:
                                uic_value = int(raw_uic)
                                logger.debug(f"Using UIC from raw_data for {broker_asset.symbol}: {uic_value}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Could not convert raw_data UIC to int for {broker_asset.symbol}: {raw_uic} ({e})")
                    
                    if uic_value is not None:
                        defaults['saxo_uic'] = uic_value
                        logger.info(f"✅ UIC trouvé pour {broker_asset.symbol}: saxo_uic={uic_value} (broker_id={broker_asset.broker_id}, raw_data.uic={broker_asset.raw_data.get('uic') if hasattr(broker_asset, 'raw_data') and broker_asset.raw_data else 'N/A'})")
                    else:
                        logger.warning(f"⚠️  No valid UIC found for Saxo asset {broker_asset.symbol} (broker_id={broker_asset.broker_id}, raw_data={broker_asset.raw_data if hasattr(broker_asset, 'raw_data') else 'N/A'})")
                elif platform == 'BINANCE':
                    if hasattr(broker_asset, 'base_asset'):
                        defaults['binance_base_asset'] = broker_asset.base_asset or ''
                    if hasattr(broker_asset, 'quote_asset'):
                        defaults['binance_quote_asset'] = broker_asset.quote_asset or ''
                    if hasattr(broker_asset, 'status'):
                        defaults['binance_status'] = broker_asset.status or ''
                
                key = (broker_asset.symbol, platform)
                existing = existing_assets.get(key)
                
                if existing:
                    if update_existing:
                        # Update existing asset
                        old_uic = existing.saxo_uic if hasattr(existing, 'saxo_uic') else None
                        # Exclure symbole_yahoo pour préserver la validation Yahoo existante
                        for key, value in defaults.items():
                            if key != 'symbole_yahoo':
                                setattr(existing, key, value)
                                # Log spécifique pour saxo_uic
                                if key == 'saxo_uic' and value is not None:
                                    logger.info(f"✅ Setting saxo_uic={value} for existing asset {existing.symbol} (ID: {existing.id}, old_uic={old_uic})")
                        assets_to_update.append(existing)
                else:
                    # Create new asset
                    # Pour SAXO, s'assurer que les champs Binance sont des chaînes vides et non None
                    asset_defaults = defaults.copy()
                    if platform == 'SAXO':
                        # Ne pas inclure les champs Binance pour SAXO (seront None par défaut)
                        # Django utilisera blank=True donc chaîne vide
                        pass  # On laisse Django gérer avec blank=True
                    elif platform == 'BINANCE':
                        # Pour BINANCE, s'assurer que les champs sont présents (déjà dans defaults)
                        pass
                    
                    new_asset = AllAssets(
                        symbol=broker_asset.symbol,
                        platform=platform,
                        **asset_defaults
                    )
                    # Pour SAXO, initialiser explicitement les champs Binance à '' si non présents
                    if platform == 'SAXO':
                        if not hasattr(new_asset, 'binance_base_asset') or new_asset.binance_base_asset is None:
                            new_asset.binance_base_asset = ''
                        if not hasattr(new_asset, 'binance_quote_asset') or new_asset.binance_quote_asset is None:
                            new_asset.binance_quote_asset = ''
                        if not hasattr(new_asset, 'binance_status') or new_asset.binance_status is None:
                            new_asset.binance_status = ''
                    
                    if platform == 'SAXO' and 'saxo_uic' in asset_defaults and asset_defaults['saxo_uic'] is not None:
                        logger.info(f"✅ Creating new asset {broker_asset.symbol} with saxo_uic={asset_defaults['saxo_uic']}")
                    assets_to_create.append(new_asset)
                    
            except Exception as e:
                errors.append({
                    'symbol': broker_asset.symbol if hasattr(broker_asset, 'symbol') else 'unknown',
                    'error': str(e),
                })
                logger.warning(f"Error preparing asset for bulk operation: {e}")
        
        # Perform bulk operations in batches
        # On utilise bulk_create et bulk_update car on a déjà séparé les assets existants des nouveaux
        if assets_to_create:
            logger.info(f"📦 Creating {len(assets_to_create)} new assets for {platform}")
            sax_assets_with_uic = [a for a in assets_to_create if hasattr(a, 'saxo_uic') and getattr(a, 'saxo_uic', None) is not None]
            if sax_assets_with_uic:
                logger.info(f"   → {len(sax_assets_with_uic)} assets avec saxo_uic dans ce batch")
            
            for i in range(0, len(assets_to_create), batch_size):
                batch = assets_to_create[i:i + batch_size]
                try:
                    uic_count = sum(1 for a in batch if hasattr(a, 'saxo_uic') and getattr(a, 'saxo_uic', None) is not None)
                    logger.info(f"   → Bulk creating batch {i//batch_size + 1} ({len(batch)} assets, {uic_count} with UIC)")
                    
                    # Utiliser bulk_create directement - on sait que ces assets n'existent pas
                    # car on les a déjà filtrés avec existing_assets
                    AllAssets.objects.bulk_create(batch, ignore_conflicts=False)
                    created += len(batch)
                except Exception as e:
                    logger.error(f"Error in bulk_create batch: {e}", exc_info=True)
                    # Fallback to individual creates en cas d'erreur
                    for asset in batch:
                        try:
                            asset.save()
                            created += 1
                        except Exception as e2:
                            errors.append({
                                'symbol': asset.symbol,
                                'error': str(e2),
                            })
        
        if assets_to_update and update_existing:
            # Get fields to update (dynamically based on what's actually in defaults)
            # Base fields always updated
            update_fields = ['name', 'asset_type', 'exchange', 'currency', 'is_tradable', 'last_updated']
            
            # Add platform-specific fields only if they exist in any asset's defaults
            # Check first asset in batch to see what fields are available
            if assets_to_update:
                # Sample first asset to see what fields might need updating
                sample_asset = assets_to_update[0]
                if platform == 'SAXO':
                    # Always include saxo_uic if platform is SAXO (will update to None if not set)
                    if 'saxo_uic' not in update_fields:
                        update_fields.append('saxo_uic')
                elif platform == 'BINANCE':
                    if hasattr(sample_asset, 'binance_base_asset'):
                        if 'binance_base_asset' not in update_fields:
                            update_fields.append('binance_base_asset')
                    if hasattr(sample_asset, 'binance_quote_asset'):
                        if 'binance_quote_asset' not in update_fields:
                            update_fields.append('binance_quote_asset')
                    if hasattr(sample_asset, 'binance_status'):
                        if 'binance_status' not in update_fields:
                            update_fields.append('binance_status')
            
            logger.info(f"🔄 Updating {len(assets_to_update)} existing assets for {platform}")
            logger.debug(f"Bulk update fields for {platform}: {update_fields}")
            
            # Compter les assets avec UIC avant update
            uic_count_before = sum(1 for a in assets_to_update if hasattr(a, 'saxo_uic') and getattr(a, 'saxo_uic', None) is not None)
            if uic_count_before > 0:
                logger.info(f"   → {uic_count_before} assets avec saxo_uic à mettre à jour")
            
            for i in range(0, len(assets_to_update), batch_size):
                batch = assets_to_update[i:i + batch_size]
                try:
                    # Log UIC updates before bulk_update
                    for asset in batch:
                        if hasattr(asset, 'saxo_uic') and asset.saxo_uic is not None:
                            logger.info(f"   → Asset {asset.symbol} (ID: {asset.id}) will be updated with saxo_uic={asset.saxo_uic}")
                    AllAssets.objects.bulk_update(batch, update_fields)
                    updated += len(batch)
                    logger.info(f"   ✅ Bulk updated batch {i//batch_size + 1} ({len(batch)} assets)")
                except Exception as e:
                    logger.error(f"Error in bulk_update batch: {e}")
                    # Fallback to individual updates
                    for asset in batch:
                        try:
                            asset.save(update_fields=update_fields)
                            updated += 1
                        except Exception as e2:
                            errors.append({
                                'symbol': asset.symbol,
                                'error': str(e2),
                            })
        
        return {
            'created': created,
            'updated': updated,
            'errors': errors,
        }
    
    def _process_asset(
        self,
        broker_asset: BrokerAsset,
        platform: str,
        update_existing: bool
    ) -> str:
        """
        Process a single asset (legacy method, kept for compatibility).
        
        Args:
            broker_asset: BrokerAsset from broker
            platform: Platform identifier
            update_existing: Whether to update if exists
            
        Returns:
            'created', 'updated', or 'skipped'
        """
        defaults = {
            'name': broker_asset.name,
            'asset_type': broker_asset.asset_type,
            'exchange': broker_asset.exchange,
            'currency': broker_asset.currency,
            'is_tradable': broker_asset.is_tradable,
        }
        
        # Add broker-specific fields
        if platform == 'SAXO':
            # Récupérer l'UIC depuis broker_id ou raw_data
            uic_value = None
            
            # Essayer depuis broker_id d'abord
            if broker_asset.broker_id and broker_asset.broker_id != 'None' and broker_asset.broker_id.strip():
                try:
                    uic_value = int(broker_asset.broker_id)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not convert broker_id to int for {broker_asset.symbol}: {broker_asset.broker_id} ({e})")
            
            # Fallback: vérifier dans raw_data (plus fiable car c'est la valeur brute de l'API)
            if uic_value is None and hasattr(broker_asset, 'raw_data') and broker_asset.raw_data:
                raw_uic = broker_asset.raw_data.get('uic')
                if raw_uic is not None and raw_uic != '':
                    try:
                        uic_value = int(raw_uic)
                        logger.debug(f"Using UIC from raw_data for {broker_asset.symbol}: {uic_value}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert raw_data UIC to int for {broker_asset.symbol}: {raw_uic} ({e})")
            
            if uic_value is not None:
                defaults['saxo_uic'] = uic_value
                logger.debug(f"Setting saxo_uic={uic_value} for Saxo asset {broker_asset.symbol}")
            else:
                logger.warning(f"No valid UIC found for Saxo asset {broker_asset.symbol} (broker_id={broker_asset.broker_id}, raw_data.uic={broker_asset.raw_data.get('uic') if hasattr(broker_asset, 'raw_data') and broker_asset.raw_data else 'N/A'})")
        
        # Check if exists
        existing = AllAssets.objects.filter(
            symbol=broker_asset.symbol,
            platform=platform
        ).first()
        
        if existing:
            if update_existing:
                for key, value in defaults.items():
                    setattr(existing, key, value)
                existing.save()
                return 'updated'
            return 'skipped'
        else:
            AllAssets.objects.create(
                symbol=broker_asset.symbol,
                platform=platform,
                **defaults
            )
            return 'created'
    
    @transaction.atomic
    def sync_all_asset_types(
        self,
        broker_account: BrokerAccount,
        limit_per_type: int = 20000,
        incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Sync all asset types from a broker.
        
        Args:
            broker_account: BrokerAccount model instance
            limit_per_type: Max assets per type
            incremental: If True, only sync assets modified since last sync
            
        Returns:
            Dict with aggregated sync results including duration and statistics
        """
        start_time = time.time()
        broker_type = broker_account.get_broker_type().upper()
        
        # Define asset types based on broker
        if broker_type == 'SAXO':
            asset_types = ['Stock', 'ETF', 'FX', 'CFD']
        elif broker_type == 'BINANCE':
            asset_types = ['Crypto']
        else:
            asset_types = ['Stock']
        
        total_created = 0
        total_updated = 0
        total_processed = 0
        all_errors = []
        results_by_type = {}
        has_failures = False
        success_count = 0
        total_duration_ms = 0
        
        for asset_type in asset_types:
            result = self.sync_assets(
                broker_account,
                asset_type=asset_type,
                limit=limit_per_type,
                incremental=incremental
            )
            
            if result.get('success'):
                success_count += 1
                total_created += result.get('created', 0)
                total_updated += result.get('updated', 0)
                total_processed += result.get('total_processed', 0)
                total_duration_ms += result.get('duration_ms', 0)
            else:
                has_failures = True
                # Ajouter l'erreur d'authentification/échec à la liste des erreurs
                error_msg = result.get('message', f'Sync failed for {asset_type}')
                all_errors.append({
                    'asset_type': asset_type,
                    'error': error_msg,
                })
            
            all_errors.extend(result.get('errors', []))
            results_by_type[asset_type] = {
                'success': result.get('success', False),
                'created': result.get('created', 0),
                'updated': result.get('updated', 0),
                'total_processed': result.get('total_processed', 0),
                'duration_ms': result.get('duration_ms', 0),
                'errors_count': len(result.get('errors', [])),
            }
        
        total_duration_ms = int((time.time() - start_time) * 1000)
        
        # Si toutes les synchronisations ont échoué, retourner un échec
        if success_count == 0:
            return {
                'success': False,
                'message': f'Échec de la synchronisation pour tous les types d\'assets. Dernière erreur: {all_errors[-1].get("error", "Unknown error") if all_errors else "Unknown error"}',
                'total_created': 0,
                'total_updated': 0,
                'total_processed': 0,
                'errors': all_errors,
                'by_type': results_by_type,
                'duration_ms': total_duration_ms,
            }
        
        # Au moins une synchronisation a réussi
        message = f'Synchronisé {total_created + total_updated} assets sur {success_count}/{len(asset_types)} types'
        if has_failures:
            message += f' ({len(asset_types) - success_count} type(s) en échec)'
        
        return {
            'success': True,
            'message': message,
            'total_created': total_created,
            'total_updated': total_updated,
            'total_processed': total_processed,
            'errors': all_errors,
            'by_type': results_by_type,
            'duration_ms': total_duration_ms,
            'broker_name': broker_account.name or broker_account.get_broker_type(),
            'broker_type': broker_type,
        }
    
    def search_and_sync(
        self,
        broker_account: BrokerAccount,
        keywords: str,
        asset_type: str = 'Stock',
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for assets and sync matching ones.
        
        Args:
            broker_account: BrokerAccount model instance
            keywords: Search keywords
            asset_type: Type of asset
            limit: Max results
            
        Returns:
            Dict with sync results and matched assets
        """
        result = self.sync_assets(
            broker_account,
            asset_type=asset_type,
            keywords=keywords,
            limit=limit
        )
        
        # Get the synced assets from database
        platform = broker_account.get_broker_type().upper()
        synced_assets = AllAssets.objects.filter(
            platform=platform,
            symbol__icontains=keywords
        )[:limit]
        
        result['synced_assets'] = list(synced_assets.values(
            'id', 'symbol', 'name', 'asset_type', 'currency'
        ))
        
        return result
    
    def _get_credentials(self, broker_account: BrokerAccount) -> Dict[str, Any]:
        """
        Get credentials from broker account.
        Utilise la méthode get_credentials_dict() du modèle pour garantir
        le bon mapping des champs selon le type de broker.
        """
        # Utiliser la méthode du modèle qui gère déjà le mapping correct
        credentials = broker_account.get_credentials_dict()
        
        # Ajouter des informations supplémentaires si nécessaire
        if broker_account.extra_credentials:
            credentials.update(broker_account.extra_credentials)
        
        # S'assurer que les paramètres d'environnement sont corrects
        broker_type = broker_account.get_broker_type().upper()
        if broker_type == 'SAXO':
            if 'environment' not in credentials:
                # ✅ MIGRATION: Utiliser saxo_environment si disponible, sinon basé sur is_sandbox
                if hasattr(broker_account, 'saxo_environment') and broker_account.saxo_environment:
                    credentials['environment'] = broker_account.saxo_environment
                else:
                    credentials['environment'] = 'simulation' if broker_account.is_sandbox else 'live'
        elif broker_type == 'BINANCE':
            if 'testnet' not in credentials:
                credentials['testnet'] = broker_account.is_sandbox or broker_account.binance_testnet
        
        return credentials
    
    def _authenticate_with_retry(
        self,
        broker,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ) -> bool:
        """
        Authenticate with broker, retrying on failure.
        
        Args:
            broker: Broker instance
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if authentication succeeded, False otherwise
        """
        import time
        
        for attempt in range(max_retries + 1):
            try:
                if broker.authenticate():
                    return True
                if attempt < max_retries:
                    logger.warning(
                        f"Authentication attempt {attempt + 1} failed, retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Authentication error on attempt {attempt + 1}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
        
        return False
    
    def _filter_incremental_assets(
        self,
        broker_assets: List[BrokerAsset],
        broker_account: BrokerAccount,
        asset_type: str
    ) -> List[BrokerAsset]:
        """
        Filter assets for incremental sync (only new or modified since last sync).
        
        Args:
            broker_assets: List of assets from broker
            broker_account: BrokerAccount instance
            asset_type: Asset type being synced
            
        Returns:
            Filtered list of assets to sync
        """
        # Get last sync time for this broker and asset type
        last_sync = BrokerSyncLog.objects.filter(
            broker_account=broker_account,
            sync_type='assets',
            status='success'
        ).order_by('-completed_at').first()
        
        if not last_sync or not last_sync.completed_at:
            # No previous sync, return all assets
            return broker_assets
        
        # Get existing assets updated since last sync
        platform = broker_account.get_broker_type().upper()
        existing_symbols = set(
            AllAssets.objects.filter(
                platform=platform,
                asset_type=asset_type,
                last_updated__gte=last_sync.completed_at
            ).values_list('symbol', flat=True)
        )
        
        # Filter out assets that haven't changed
        # For now, we'll sync all assets (incremental logic can be enhanced later)
        # This is a placeholder for future incremental sync logic
        return broker_assets
    
    def _log_sync(
        self,
        broker_account: BrokerAccount,
        sync_type: str,
        status: str,
        records_synced: int = 0,
        error_message: str = '',
        details: Optional[Dict] = None
    ) -> BrokerSyncLog:
        """Log a sync operation."""
        return BrokerSyncLog.objects.create(
            broker_account=broker_account,
            sync_type=sync_type,
            status=status,
            records_synced=records_synced,
            error_message=error_message,
            details=details or {},
        )

