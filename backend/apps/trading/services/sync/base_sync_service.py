"""
Base Synchronization Service.

This abstract class provides the foundation for all synchronization services,
with common functionality for logging, error handling, and result tracking.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone

from ...models import BrokerAccount, BrokerSyncLog
from ...exceptions import SyncException, SyncPartialError

logger = logging.getLogger('trading.services.sync')


class BaseSyncService(ABC):
    """
    Abstract base class for all synchronization services.
    
    Provides:
    - Common logging methods
    - Error tracking and aggregation
    - Sync log creation
    - Result standardization
    
    Subclasses must implement:
    - sync(): Main synchronization method
    """
    
    # Override in subclass
    SYNC_TYPE: str = 'unknown'
    
    def __init__(self, user: User):
        """
        Initialize the sync service.
        
        Args:
            user: Django User instance
        """
        self.user = user
        self.logger = logging.getLogger(f'trading.sync.{self.__class__.__name__}')
        
        # Track sync progress
        self._errors: List[Dict[str, Any]] = []
        self._warnings: List[str] = []
        self._start_time: Optional[datetime] = None
    
    @abstractmethod
    def sync(self, broker_account: BrokerAccount, **kwargs) -> Dict[str, Any]:
        """
        Main synchronization method.
        
        Args:
            broker_account: BrokerAccount to sync from
            **kwargs: Additional sync parameters
            
        Returns:
            Dict with sync results
        """
        pass
    
    # ============================================
    # LOGGING HELPERS
    # ============================================
    
    def _log_start(self, message: str = None, **extra):
        """Log sync start."""
        self._start_time = timezone.now()
        self._errors = []
        self._warnings = []
        
        msg = message or f"Starting {self.SYNC_TYPE} sync"
        self.logger.info(f"🔄 {msg}", extra=extra)
    
    def _log_success(self, message: str, **extra):
        """Log a success message."""
        self.logger.info(f"✅ {message}", extra=extra)
    
    def _log_error(self, message: str, error: Optional[Exception] = None, **extra):
        """Log an error and track it."""
        error_data = {
            'message': message,
            'error': str(error) if error else None,
            'timestamp': timezone.now().isoformat(),
            **extra
        }
        self._errors.append(error_data)
        
        if error:
            self.logger.error(f"❌ {message}: {error}", exc_info=True, extra=extra)
        else:
            self.logger.error(f"❌ {message}", extra=extra)
    
    def _log_warning(self, message: str, **extra):
        """Log a warning and track it."""
        self._warnings.append(message)
        self.logger.warning(f"⚠️ {message}", extra=extra)
    
    def _log_complete(self, created: int = 0, updated: int = 0, **extra):
        """Log sync completion with summary."""
        duration = None
        if self._start_time:
            duration = (timezone.now() - self._start_time).total_seconds()
        
        msg = f"{self.SYNC_TYPE} sync completed: {created} created, {updated} updated"
        if self._errors:
            msg += f", {len(self._errors)} errors"
        if duration:
            msg += f" ({duration:.2f}s)"
        
        self.logger.info(f"🏁 {msg}", extra=extra)
    
    # ============================================
    # SYNC LOG HELPERS
    # ============================================
    
    def _create_sync_log(
        self,
        broker_account: BrokerAccount,
        status: str,
        records_synced: int = 0,
        error_message: str = '',
        details: Optional[Dict] = None
    ) -> BrokerSyncLog:
        """
        Create a sync log entry.
        
        Args:
            broker_account: BrokerAccount that was synced
            status: Sync status ('success', 'error', 'partial')
            records_synced: Number of records synced
            error_message: Error message if any
            details: Additional details dict
            
        Returns:
            BrokerSyncLog instance
        """
        # Map status to model choices
        status_map = {
            'success': 'SUCCESS',
            'error': 'FAILED',
            'partial': 'PARTIAL',
            'warning': 'PARTIAL',
        }
        
        return BrokerSyncLog.objects.create(
            broker_account=broker_account,
            sync_type=self.SYNC_TYPE,
            status=status_map.get(status.lower(), 'FAILED'),
            records_synced=records_synced,
            error_message=error_message,
            details=details or {},
            completed_at=timezone.now() if status != 'error' else None,
        )
    
    # ============================================
    # RESULT HELPERS
    # ============================================
    
    def _build_result(
        self,
        success: bool,
        created: int = 0,
        updated: int = 0,
        deleted: int = 0,
        message: str = '',
        **extra
    ) -> Dict[str, Any]:
        """
        Build a standardized result dictionary.
        
        Args:
            success: Whether sync was successful
            created: Number of records created
            updated: Number of records updated
            deleted: Number of records deleted
            message: Result message
            **extra: Additional data to include
            
        Returns:
            Standardized result dict
        """
        result = {
            'success': success,
            'created': created,
            'updated': updated,
            'deleted': deleted,
            'total': created + updated,
            'message': message or self._build_message(success, created, updated),
        }
        
        # Add errors if any
        if self._errors:
            result['errors'] = self._errors[:10]  # Limit to 10
            result['error_count'] = len(self._errors)
        
        # Add warnings if any
        if self._warnings:
            result['warnings'] = self._warnings[:10]
            result['warning_count'] = len(self._warnings)
        
        # Add duration
        if self._start_time:
            result['duration_seconds'] = (timezone.now() - self._start_time).total_seconds()
        
        # Add extra data
        result.update(extra)
        
        return result
    
    def _build_message(self, success: bool, created: int, updated: int) -> str:
        """Build a result message."""
        if not success:
            return f"{self.SYNC_TYPE} sync failed"
        
        parts = []
        if created:
            parts.append(f"{created} created")
        if updated:
            parts.append(f"{updated} updated")
        
        if parts:
            return f"{self.SYNC_TYPE} sync completed: " + ", ".join(parts)
        return f"{self.SYNC_TYPE} sync completed with no changes"
    
    def _raise_if_all_failed(self, total: int, failed: int):
        """
        Raise SyncException if all items failed.
        
        Args:
            total: Total items attempted
            failed: Number of failures
        """
        if total > 0 and failed == total:
            raise SyncException(
                message=f"All {total} items failed to sync",
                sync_type=self.SYNC_TYPE,
                details={'errors': self._errors[:10]}
            )
    
    def _raise_if_partial(self, succeeded: int, failed: int):
        """
        Raise SyncPartialError if some items failed.
        
        Args:
            succeeded: Number of successes
            failed: Number of failures
        """
        if failed > 0 and succeeded > 0:
            raise SyncPartialError(
                sync_type=self.SYNC_TYPE,
                succeeded=succeeded,
                failed=failed,
                errors=self._errors
            )

