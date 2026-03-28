"""
Service pour préparer et formater les données de trading pour l'analyse IA.
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from apps.trading.models import Strategy, Position, Trade, AllAssets, StrategyPerformance
from apps.ai_assistant.services.prompt_templates import (
    format_strategy_prompt,
    format_portfolio_prompt,
    format_asset_prompt
)
from apps.ai_assistant.services.gemini_service import GeminiAIService
from apps.ai_assistant.models import AIAnalysis

logger = logging.getLogger('ai_assistant')


class TradingAnalysisService:
    """
    Service pour analyser les données de trading avec l'IA.
    Prépare les données, génère les prompts, et parse les résultats.
    """
    
    def __init__(self):
        """Initialise le service d'analyse trading."""
        self.gemini_service = GeminiAIService()
    
    def analyze_strategy(self, strategy: Strategy, user: User) -> AIAnalysis:
        """
        Analyse une stratégie spécifique.
        
        Args:
            strategy: Stratégie à analyser
            user: Utilisateur propriétaire
        
        Returns:
            AIAnalysis: Objet d'analyse créé
        """
        logger.info(f"Début de l'analyse IA pour la stratégie {strategy.name}")
        
        # Créer l'objet d'analyse
        analysis = AIAnalysis.objects.create(
            user=user,
            analysis_type=AIAnalysis.AnalysisType.STRATEGY,
            status=AIAnalysis.AnalysisStatus.PROCESSING,
            strategy=strategy,
            prompt=""  # Sera rempli après
        )
        
        try:
            # Préparer les données
            strategy_data = self._prepare_strategy_data(strategy)
            
            # Générer le prompt
            prompt = format_strategy_prompt(strategy_data)
            analysis.prompt = prompt
            analysis.save(update_fields=['prompt'])
            
            # Générer l'analyse avec l'IA
            result = self.gemini_service.generate_analysis(prompt)
            
            if result['success']:
                # Parser et sauvegarder les résultats
                self._save_analysis_results(analysis, result)
                analysis.mark_as_completed()
                logger.info(f"Analyse de stratégie {strategy.name} terminée avec succès")
            else:
                analysis.mark_as_failed(result['error'])
                logger.error(f"Échec de l'analyse: {result['error']}")
        
        except Exception as e:
            error_msg = f"Erreur lors de l'analyse: {str(e)}"
            logger.error(error_msg)
            analysis.mark_as_failed(error_msg)
        
        return analysis
    
    def analyze_portfolio(self, user: User) -> AIAnalysis:
        """
        Analyse le portefeuille complet d'un utilisateur.
        
        Args:
            user: Utilisateur dont analyser le portefeuille
        
        Returns:
            AIAnalysis: Objet d'analyse créé
        """
        logger.info(f"Début de l'analyse IA du portefeuille pour l'utilisateur {user.username}")
        
        # Créer l'objet d'analyse
        analysis = AIAnalysis.objects.create(
            user=user,
            analysis_type=AIAnalysis.AnalysisType.PORTFOLIO,
            status=AIAnalysis.AnalysisStatus.PROCESSING,
            prompt=""
        )
        
        try:
            # Préparer les données
            portfolio_data = self._prepare_portfolio_data(user)
            
            # Générer le prompt
            prompt = format_portfolio_prompt(portfolio_data)
            analysis.prompt = prompt
            analysis.save(update_fields=['prompt'])
            
            # Générer l'analyse avec l'IA
            result = self.gemini_service.generate_analysis(prompt)
            
            if result['success']:
                self._save_analysis_results(analysis, result)
                analysis.mark_as_completed()
                logger.info(f"Analyse de portefeuille pour {user.username} terminée avec succès")
            else:
                analysis.mark_as_failed(result['error'])
                logger.error(f"Échec de l'analyse: {result['error']}")
        
        except Exception as e:
            error_msg = f"Erreur lors de l'analyse: {str(e)}"
            logger.error(error_msg)
            analysis.mark_as_failed(error_msg)
        
        return analysis
    
    def _prepare_strategy_data(self, strategy: Strategy) -> Dict:
        """Prépare les données d'une stratégie pour le prompt."""
        # Récupérer les positions
        positions = Position.objects.filter(strategy=strategy, is_open=True)
        
        # Récupérer les trades récents (30 derniers jours)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_trades = Trade.objects.filter(
            user=strategy.user,
            executed_at__gte=thirty_days_ago
        ).order_by('-executed_at')[:20]
        
        # Récupérer les performances récentes
        recent_performances = StrategyPerformance.objects.filter(
            strategy=strategy,
            date__gte=thirty_days_ago.date()
        ).order_by('-date')[:30]
        
        # Formater les données
        return {
            'strategy_name': strategy.name,
            'algorithm_type': strategy.get_algorithm_type_display(),
            'asset_symbol': strategy.all_asset.symbol if strategy.all_asset else 'N/A',
            'asset_name': strategy.all_asset.name if strategy.all_asset else 'N/A',
            'risk_level': strategy.get_risk_level_display(),
            'is_active': 'Active' if strategy.is_active else 'Inactive',
            'parameters': self._format_parameters(strategy),
            'performance_data': self._format_performance(recent_performances),
            'positions_data': self._format_positions(positions),
            'trades_data': self._format_trades(recent_trades)
        }
    
    def _prepare_portfolio_data(self, user: User) -> Dict:
        """Prépare les données du portefeuille pour le prompt."""
        # Récupérer toutes les stratégies actives
        strategies = Strategy.objects.filter(user=user, is_active=True)
        
        # Récupérer toutes les positions ouvertes
        positions = Position.objects.filter(user=user, is_open=True)
        
        # Calculer les métriques globales
        total_pnl = sum(p.pnl or 0 for p in positions)
        total_value = sum(
            float(p.quantity * p.current_price) if p.current_price else 0
            for p in positions
        )
        
        # Calcul du P&L en pourcentage
        total_invested = sum(
            float(p.quantity * p.entry_price) for p in positions
        )
        total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Analyser la diversification
        diversification = self._analyze_diversification(positions)
        
        # Performances récentes
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_performances = StrategyPerformance.objects.filter(
            strategy__user=user,
            date__gte=thirty_days_ago.date()
        ).order_by('-date')
        
        return {
            'num_strategies': strategies.count(),
            'num_positions': positions.count(),
            'total_position_value': f"{total_value:.2f}",
            'total_pnl': f"{total_pnl:.2f}",
            'total_pnl_percent': f"{total_pnl_percent:.2f}",
            'strategies_data': self._format_strategies(strategies),
            'positions_data': self._format_positions(positions),
            'diversification_data': diversification,
            'performance_data': self._format_performance(recent_performances)
        }
    
    def _format_parameters(self, strategy: Strategy) -> str:
        """Formate les paramètres d'une stratégie."""
        params = strategy.get_parameters_dict()
        if not params:
            return "Aucun paramètre configuré"
        
        lines = []
        for key, value in params.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    def _format_performance(self, performances) -> str:
        """Formate les données de performance."""
        if not performances:
            return "Aucune donnée de performance disponible"
        
        lines = []
        for perf in performances:
            lines.append(
                f"- {perf.date}: P&L net = {perf.net_pnl}€, "
                f"Trades gagnants = {perf.winning_trades}, "
                f"Trades perdants = {perf.losing_trades}"
            )
        return "\n".join(lines)
    
    def _format_positions(self, positions) -> str:
        """Formate les positions."""
        if not positions:
            return "Aucune position ouverte"
        
        lines = []
        for pos in positions:
            pnl = pos.pnl or 0
            pnl_pct = pos.pnl_percent or 0
            lines.append(
                f"- {pos.all_asset.symbol if pos.all_asset else 'Unknown'}: "
                f"{pos.side} {pos.quantity} @ {pos.entry_price}€ "
                f"(Prix actuel: {pos.current_price}€, P&L: {pnl:.2f}€ / {pnl_pct:.2f}%)"
            )
        return "\n".join(lines)
    
    def _format_trades(self, trades) -> str:
        """Formate les trades."""
        if not trades:
            return "Aucun trade récent"
        
        lines = []
        for trade in trades:
            lines.append(
                f"- {trade.executed_at.strftime('%Y-%m-%d %H:%M')}: "
                f"{trade.trade_type} {trade.quantity} "
                f"{trade.all_asset.symbol if trade.all_asset else 'Unknown'} "
                f"@ {trade.price}€ (Frais: {trade.fees}€)"
            )
        return "\n".join(lines)
    
    def _format_strategies(self, strategies) -> str:
        """Formate la liste des stratégies."""
        if not strategies:
            return "Aucune stratégie active"
        
        lines = []
        for strat in strategies:
            lines.append(
                f"- {strat.name} ({strat.get_algorithm_type_display()}) "
                f"sur {strat.all_asset.symbol if strat.all_asset else 'Unknown'} "
                f"- Risque: {strat.get_risk_level_display()}"
            )
        return "\n".join(lines)
    
    def _analyze_diversification(self, positions) -> str:
        """Analyse la diversification du portefeuille."""
        if not positions:
            return "Aucune position pour analyser la diversification"
        
        # Compter les actifs uniques
        assets = {}
        for pos in positions:
            symbol = pos.all_asset.symbol if pos.all_asset else 'Unknown'
            value = float(pos.quantity * (pos.current_price or pos.entry_price))
            assets[symbol] = assets.get(symbol, 0) + value
        
        total = sum(assets.values())
        
        lines = ["Distribution des actifs:"]
        for symbol, value in sorted(assets.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total * 100) if total > 0 else 0
            lines.append(f"- {symbol}: {value:.2f}€ ({pct:.1f}%)")
        
        return "\n".join(lines)
    
    def _save_analysis_results(self, analysis: AIAnalysis, result: Dict):
        """Sauvegarde les résultats de l'analyse."""
        analysis.response = result['response']
        analysis.metadata = result['metadata']
        
        # Parser les données structurées
        parsed = result['parsed_data']
        
        if parsed:
            analysis.summary = parsed.get('summary', '')
            analysis.recommendations = parsed.get('recommendations', [])
            analysis.insights = {
                'pnl_analysis': parsed.get('pnl_analysis', ''),
                'parameter_evaluation': parsed.get('parameter_evaluation', ''),
                'diversification_analysis': parsed.get('diversification_analysis', ''),
                'risk_assessment': parsed.get('risk_assessment', ''),
                'technical_analysis': parsed.get('technical_analysis', ''),
                'strategy_performance': parsed.get('strategy_performance', '')
            }
            analysis.risks = parsed.get('risks', [])
            analysis.opportunities = parsed.get('opportunities', [])
            analysis.confidence_score = parsed.get('confidence_score', None)
        
        analysis.save()
