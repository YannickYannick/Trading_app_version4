"""
Service pour récupérer les positions historiques depuis les transactions Saxo.

Ce service remplace complètement l'usage de hist/v3/positions par une logique
basée uniquement sur hist/v1/transactions.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.contrib.auth.models import User
import logging

from ..brokers.saxo import SaxoBroker
from .saxo_position_reconstructor import PositionReconstructor, ReconstructedPosition

logger = logging.getLogger('trading.services.saxo_historical_positions')


class SaxoHistoricalPositionsService:
    """
    Service pour obtenir les positions historiques depuis les transactions.
    
    Utilisation:
        service = SaxoHistoricalPositionsService(user)
        positions = service.get_closed_positions(
            broker_account=account,
            from_date='2025-01-01',
            to_date='2025-12-31'
        )
    """
    
    def __init__(self, user: User):
        """
        Initialiser le service.
        
        Args:
            user: Utilisateur Django
        """
        self.user = user
    
    def get_closed_positions(
        self,
        broker_account,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 10000
    ) -> List[ReconstructedPosition]:
        """
        Récupérer les positions fermées reconstruites depuis les transactions.
        
        Args:
            broker_account: BrokerAccount Saxo
            from_date: Date de début (format ISO, optionnel)
            to_date: Date de fin (format ISO, optionnel)
            limit: Nombre maximum de transactions à récupérer
            
        Returns:
            Liste de positions fermées reconstruites
        """
        try:
            # Obtenir le broker instance
            credentials = broker_account.get_credentials_dict()
            broker = SaxoBroker(self.user, credentials)
            
            # Authentifier
            if not broker.authenticate():
                raise Exception("Failed to authenticate with Saxo")
            
            # Récupérer les transactions
            transactions = broker.get_transactions(
                from_date=from_date,
                to_date=to_date,
                limit=limit
            )
            
            # Reconstruire les positions
            reconstructor = PositionReconstructor(transactions)
            positions = reconstructor.reconstruct()
            
            # Filtrer uniquement les positions fermées
            closed_positions = [pos for pos in positions if pos.is_closed]
            
            logger.info(f"Reconstructed {len(closed_positions)} closed positions from {len(transactions)} transactions")
            return closed_positions
            
        except Exception as e:
            logger.error(f"Error getting closed positions: {e}", exc_info=True)
            raise
    
    def get_all_positions(
        self,
        broker_account,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 10000
    ) -> Dict[str, List[ReconstructedPosition]]:
        """
        Récupérer toutes les positions (ouvertes et fermées).
        
        Returns:
            Dict avec 'open' et 'closed' listes de positions
        """
        try:
            credentials = broker_account.get_credentials_dict()
            broker = SaxoBroker(self.user, credentials)
            
            if not broker.authenticate():
                raise Exception("Failed to authenticate with Saxo")
            
            transactions = broker.get_transactions(
                from_date=from_date,
                to_date=to_date,
                limit=limit
            )
            
            reconstructor = PositionReconstructor(transactions)
            positions = reconstructor.reconstruct()
            
            open_positions = [pos for pos in positions if not pos.is_closed]
            closed_positions = [pos for pos in positions if pos.is_closed]
            
            return {
                'open': open_positions,
                'closed': closed_positions,
                'total': positions
            }
            
        except Exception as e:
            logger.error(f"Error getting all positions: {e}", exc_info=True)
            raise
    
    def get_performance_metrics(
        self,
        broker_account,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculer les métriques de performance à partir des positions reconstruites.
        
        Returns:
            Dict avec winrate, P&L total, nombre de trades, etc.
        """
        positions = self.get_closed_positions(
            broker_account=broker_account,
            from_date=from_date,
            to_date=to_date
        )
        
        if not positions:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'winrate': 0,
                'total_gross_pnl': 0,
                'total_fees': 0,
                'total_funding': 0,
                'total_net_pnl': 0,
                'avg_trade_duration': None,
            }
        
        winning_trades = sum(1 for p in positions if p.net_pnl > 0)
        losing_trades = sum(1 for p in positions if p.net_pnl < 0)
        total_gross_pnl = sum(p.gross_pnl for p in positions)
        total_fees = sum(p.total_fees for p in positions)
        total_funding = sum(p.total_funding for p in positions)
        total_net_pnl = sum(p.net_pnl for p in positions)
        
        # Calculer la durée moyenne des trades
        durations = []
        for p in positions:
            if p.open_date and p.close_date:
                duration = (p.close_date - p.open_date).total_seconds() / 3600  # en heures
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else None
        
        return {
            'total_trades': len(positions),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'breakeven_trades': len(positions) - winning_trades - losing_trades,
            'winrate': (winning_trades / len(positions) * 100) if positions else 0,
            'total_gross_pnl': float(total_gross_pnl),
            'total_fees': float(total_fees),
            'total_funding': float(total_funding),
            'total_net_pnl': float(total_net_pnl),
            'avg_net_pnl_per_trade': float(total_net_pnl / len(positions)) if positions else 0,
            'avg_trade_duration_hours': avg_duration,
            'best_trade': float(max((p.net_pnl for p in positions), default=0)),
            'worst_trade': float(min((p.net_pnl for p in positions), default=0)),
        }











