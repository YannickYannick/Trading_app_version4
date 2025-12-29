"""
Service de reconstruction des positions Saxo à partir des transactions.

Ce module permet de reconstruire des positions (open → close) à partir des
transactions brutes de l'endpoint hist/v1/transactions, offrant un niveau
de détail supérieur à celui fourni par hist/v3/positions.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger('trading.services.saxo_position_reconstructor')


@dataclass
class ReconstructedPosition:
    """
    Position reconstruite à partir des transactions.
    
    Cette structure contient toutes les informations nécessaires pour
    remplacer complètement l'usage de hist/v3/positions.
    """
    # Identifiants (sans valeurs par défaut)
    trade_id: str  # TradeId Saxo
    uic: int  # UIC de l'instrument
    direction: str  # 'LONG' ou 'SHORT'
    quantity: Decimal  # Quantité finale de la position
    
    # Champs optionnels (avec valeurs par défaut)
    instrument_symbol: Optional[str] = None  # Symbole si disponible
    
    # Dates et prix
    open_date: Optional[datetime] = None  # Date d'ouverture
    open_price: Decimal = Decimal('0')  # Prix moyen d'ouverture
    close_date: Optional[datetime] = None  # Date de clôture
    close_price: Decimal = Decimal('0')  # Prix moyen de clôture
    
    # P&L
    gross_pnl: Decimal = Decimal('0')  # P&L brut (sans frais)
    total_fees: Decimal = Decimal('0')  # Frais totaux (commissions)
    total_funding: Decimal = Decimal('0')  # Funding total
    net_pnl: Decimal = Decimal('0')  # P&L net (brut - frais - funding)
    
    # Détails des transactions
    open_transactions: List[Dict] = None  # Transactions d'ouverture
    close_transactions: List[Dict] = None  # Transactions de clôture
    fee_transactions: List[Dict] = None  # Transactions de frais
    funding_transactions: List[Dict] = None  # Transactions de funding
    
    # Métadonnées
    is_closed: bool = False  # True si la position est fermée
    partial_closes: int = 0  # Nombre de clôtures partielles
    scaling_in_count: int = 0  # Nombre d'ajouts à la position
    
    def __post_init__(self):
        """Initialiser les listes si None"""
        if self.open_transactions is None:
            self.open_transactions = []
        if self.close_transactions is None:
            self.close_transactions = []
        if self.fee_transactions is None:
            self.fee_transactions = []
        if self.funding_transactions is None:
            self.funding_transactions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire pour sérialisation"""
        return {
            'trade_id': self.trade_id,
            'uic': self.uic,
            'instrument_symbol': self.instrument_symbol,
            'direction': self.direction,
            'quantity': float(self.quantity),
            'open_date': self.open_date.isoformat() if self.open_date else None,
            'open_price': float(self.open_price),
            'close_date': self.close_date.isoformat() if self.close_date else None,
            'close_price': float(self.close_price),
            'gross_pnl': float(self.gross_pnl),
            'total_fees': float(self.total_fees),
            'total_funding': float(self.total_funding),
            'net_pnl': float(self.net_pnl),
            'is_closed': self.is_closed,
            'partial_closes': self.partial_closes,
            'scaling_in_count': self.scaling_in_count,
            'transaction_counts': {
                'open': len(self.open_transactions),
                'close': len(self.close_transactions),
                'fees': len(self.fee_transactions),
                'funding': len(self.funding_transactions),
            }
        }


class PositionReconstructor:
    """
    Reconstructeur de positions à partir des transactions Saxo.
    
    Logique principale :
    1. Récupérer toutes les transactions depuis hist/v1/transactions
    2. Grouper par TradeId et Uic
    3. Séparer les transactions Open, Close, Fees, Funding
    4. Calculer les prix moyens d'ouverture/fermeture
    5. Calculer le P&L brut, frais, funding, net
    6. Produire des ReconstructedPosition
    """
    
    # Types de transactions d'ouverture/fermeture
    OPEN_TYPES = ['Trade', 'PositionOpen']
    CLOSE_TYPES = ['Trade', 'PositionClose']
    
    # Types de frais
    FEE_TYPES = ['Commission', 'BrokerCommission', 'TicketFee', 'FinancingFee']
    
    # Types de funding
    FUNDING_TYPES = ['Funding', 'Interest', 'Financing']
    
    def __init__(self, transactions: List[Dict[str, Any]]):
        """
        Initialiser le reconstructeur avec des transactions.
        
        Args:
            transactions: Liste de transactions depuis hist/v1/transactions
        """
        self.transactions = transactions
        self.reconstructed_positions: List[ReconstructedPosition] = []
    
    def reconstruct(self) -> List[ReconstructedPosition]:
        """
        Reconstruire toutes les positions à partir des transactions.
        
        Returns:
            Liste de positions reconstruites
        """
        logger.info(f"Reconstructing positions from {len(self.transactions)} transactions")
        
        # Étape 1: Grouper les transactions par TradeId et Uic
        grouped = self._group_transactions()
        logger.info(f"Grouped into {len(grouped)} position groups")
        
        # Étape 2: Reconstruire chaque position
        for (trade_id, uic), txns in grouped.items():
            try:
                position = self._reconstruct_single_position(trade_id, uic, txns)
                if position:
                    self.reconstructed_positions.append(position)
            except Exception as e:
                logger.error(f"Error reconstructing position TradeId={trade_id}, Uic={uic}: {e}", exc_info=True)
        
        logger.info(f"Successfully reconstructed {len(self.reconstructed_positions)} positions")
        return self.reconstructed_positions
    
    def _group_transactions(self) -> Dict[tuple, List[Dict]]:
        """
        Grouper les transactions par (TradeId, Uic).
        
        Returns:
            Dict avec clé (TradeId, Uic) et valeur liste de transactions
        """
        grouped = defaultdict(list)
        
        for txn in self.transactions:
            trade_id = txn.get('TradeId')
            uic = txn.get('Uic')
            
            # Ignorer les transactions sans TradeId ou Uic
            if not trade_id or uic is None:
                logger.debug(f"Skipping transaction without TradeId or Uic: {txn.get('TransactionId')}")
                continue
            
            grouped[(str(trade_id), int(uic))].append(txn)
        
        return dict(grouped)
    
    def _reconstruct_single_position(
        self,
        trade_id: str,
        uic: int,
        transactions: List[Dict]
    ) -> Optional[ReconstructedPosition]:
        """
        Reconstruire une position unique à partir de ses transactions.
        
        Args:
            trade_id: TradeId de la position
            uic: UIC de l'instrument
            transactions: Liste des transactions pour cette position
            
        Returns:
            ReconstructedPosition ou None en cas d'erreur
        """
        # Séparer les transactions par type
        open_txns, close_txns, fee_txns, funding_txns = self._classify_transactions(transactions)
        
        # Si aucune transaction d'ouverture, ignorer
        if not open_txns:
            logger.warning(f"No open transactions for TradeId={trade_id}, Uic={uic}")
            return None
        
        # Calculer la direction et la quantité d'abord
        direction, quantity = self._calculate_direction_and_quantity(open_txns, close_txns)
        
        # Créer la position avec tous les paramètres requis
        position = ReconstructedPosition(
            trade_id=trade_id,
            uic=uic,
            direction=direction,
            quantity=quantity,
            open_transactions=open_txns,
            close_transactions=close_txns,
            fee_transactions=fee_txns,
            funding_transactions=funding_txns,
        )
        
        # Calculer les dates et prix
        self._calculate_dates_and_prices(position, open_txns, close_txns)
        
        # Calculer les frais et funding
        self._calculate_fees_and_funding(position, fee_txns, funding_txns)
        
        # Calculer le P&L
        self._calculate_pnl(position)
        
        # Marquer si fermée
        position.is_closed = len(close_txns) > 0 and position.quantity == Decimal('0')
        position.partial_closes = len(close_txns)
        position.scaling_in_count = len(open_txns) - 1  # -1 car la première n'est pas un scaling
        
        return position
    
    def _classify_transactions(
        self,
        transactions: List[Dict]
    ) -> tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
        """
        Classifier les transactions en Open, Close, Fees, Funding.
        
        Returns:
            Tuple (open, close, fees, funding)
        """
        open_txns = []
        close_txns = []
        fee_txns = []
        funding_txns = []
        
        for txn in transactions:
            tx_type = txn.get('TransactionType', '')
            to_open_or_close = txn.get('ToOpenOrClose', '')
            funding_subtype = txn.get('FundingSubType', '')
            
            # Classification principale par ToOpenOrClose
            if to_open_or_close == 'Open':
                open_txns.append(txn)
            elif to_open_or_close == 'Close':
                close_txns.append(txn)
            
            # Classification des frais et funding
            if funding_subtype in self.FEE_TYPES or tx_type in self.FEE_TYPES:
                fee_txns.append(txn)
            elif funding_subtype in self.FUNDING_TYPES or tx_type in self.FUNDING_TYPES:
                funding_txns.append(txn)
            elif 'Fee' in funding_subtype or 'Fee' in tx_type:
                fee_txns.append(txn)
            elif 'Funding' in funding_subtype or 'Funding' in tx_type:
                funding_txns.append(txn)
        
        return open_txns, close_txns, fee_txns, funding_txns
    
    def _calculate_direction_and_quantity(
        self,
        open_txns: List[Dict],
        close_txns: List[Dict]
    ) -> tuple[str, Decimal]:
        """
        Calculer la direction et la quantité finale de la position.
        
        Returns:
            Tuple (direction, quantity)
        """
        # Calculer la quantité nette d'ouverture (peut être positive ou négative)
        open_amount = Decimal('0')
        for txn in open_txns:
            amount = Decimal(str(txn.get('Amount', 0)))
            open_amount += amount
        
        # Calculer la quantité nette de fermeture (prendre valeur absolue)
        close_amount = Decimal('0')
        for txn in close_txns:
            amount = Decimal(str(txn.get('Amount', 0)))
            # Pour les fermetures, Amount peut être négatif, prendre la valeur absolue
            close_amount += abs(amount)
        
        # Déterminer la direction à partir de l'ouverture
        # Si Amount positif = LONG, négatif = SHORT
        if open_amount > 0:
            direction = 'LONG'
            # Quantité finale = ouverture - fermeture (toutes deux positives)
            quantity = abs(open_amount) - close_amount
        elif open_amount < 0:
            direction = 'SHORT'
            # Pour SHORT, open_amount est négatif, donc on fait |open| - close
            quantity = abs(open_amount) - close_amount
        else:
            # Cas limite : pas d'ouverture
            direction = 'LONG'
            quantity = Decimal('0')
        
        # S'assurer que la quantité n'est jamais négative
        quantity = max(quantity, Decimal('0'))
        
        return direction, quantity
    
    def _calculate_dates_and_prices(
        self,
        position: ReconstructedPosition,
        open_txns: List[Dict],
        close_txns: List[Dict]
    ):
        """Calculer les dates et prix moyens d'ouverture et de fermeture"""
        # Prix moyen d'ouverture (pondéré par la quantité)
        if open_txns:
            total_value = Decimal('0')
            total_qty = Decimal('0')
            dates = []
            
            for txn in sorted(open_txns, key=lambda x: x.get('TradeDate', '')):
                amount = Decimal(str(txn.get('Amount', 0)))
                price = Decimal(str(txn.get('Price', 0)))
                trade_date = txn.get('TradeDate')
                
                if amount and price:
                    total_value += abs(amount) * price
                    total_qty += abs(amount)
                
                if trade_date:
                    try:
                        dates.append(self._parse_date(trade_date))
                    except:
                        pass
            
            if total_qty > 0:
                position.open_price = total_value / total_qty
            
            if dates:
                position.open_date = min(dates)
        
        # Prix moyen de fermeture (pondéré par la quantité)
        if close_txns:
            total_value = Decimal('0')
            total_qty = Decimal('0')
            dates = []
            
            for txn in sorted(close_txns, key=lambda x: x.get('TradeDate', '')):
                amount = Decimal(str(txn.get('Amount', 0)))
                price = Decimal(str(txn.get('Price', 0)))
                trade_date = txn.get('TradeDate')
                
                if amount and price:
                    total_value += abs(amount) * price
                    total_qty += abs(amount)
                
                if trade_date:
                    try:
                        dates.append(self._parse_date(trade_date))
                    except:
                        pass
            
            if total_qty > 0:
                position.close_price = total_value / total_qty
            
            if dates:
                position.close_date = max(dates)  # Dernière date de fermeture
    
    def _calculate_fees_and_funding(
        self,
        position: ReconstructedPosition,
        fee_txns: List[Dict],
        funding_txns: List[Dict]
    ):
        """Calculer les frais totaux et le funding total"""
        # Frais totaux
        total_fees = Decimal('0')
        for txn in fee_txns:
            # Les frais sont généralement dans AmountAccountValue (négatif)
            amount = Decimal(str(txn.get('AmountAccountValue', 0)))
            total_fees += abs(amount)  # Prendre la valeur absolue
        
        position.total_fees = total_fees
        
        # Funding total
        total_funding = Decimal('0')
        for txn in funding_txns:
            amount = Decimal(str(txn.get('AmountAccountValue', 0)))
            total_funding += amount  # Peut être positif ou négatif
        
        position.total_funding = total_funding
    
    def _calculate_pnl(self, position: ReconstructedPosition):
        """
        Calculer le P&L brut et net.
        
        Pour LONG: P&L = (close_price - open_price) * quantity_closed
        Pour SHORT: P&L = (open_price - close_price) * quantity_closed
        
        Note: La quantité utilisée pour le P&L est la quantité fermée, pas la quantité finale.
        """
        # Vérifier si la position a été fermée (au moins partiellement)
        has_closed = len(position.close_transactions) > 0
        has_prices = position.close_price > 0 and position.open_price > 0
        
        if not has_closed or not has_prices:
            # Position ouverte ou prix manquants, pas de P&L réalisé
            position.gross_pnl = Decimal('0')
            position.net_pnl = Decimal('0')
            return
        
        # Calculer la quantité fermée (toutes les fermetures)
        closed_quantity = Decimal('0')
        for txn in position.close_transactions:
            amount = Decimal(str(txn.get('Amount', 0)))
            closed_quantity += abs(amount)
        
        # Si aucune quantité fermée, pas de P&L
        if closed_quantity == 0:
            position.gross_pnl = Decimal('0')
            position.net_pnl = Decimal('0')
            return
        
        # Calculer le P&L brut
        if position.direction == 'LONG':
            position.gross_pnl = (position.close_price - position.open_price) * closed_quantity
        else:  # SHORT
            position.gross_pnl = (position.open_price - position.close_price) * closed_quantity
        
        # P&L net = brut - frais - funding
        position.net_pnl = position.gross_pnl - position.total_fees - position.total_funding
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parser une date depuis un string Saxo"""
        try:
            # Format ISO standard
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(date_str)
        except:
            # Format alternatif
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                raise ValueError(f"Unable to parse date: {date_str}")

