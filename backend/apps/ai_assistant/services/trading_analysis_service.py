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
    format_asset_prompt,
    format_diversify_prompt,
    format_sell_suggestions_prompt,
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

    def suggest_diversification(self, user: User) -> AIAnalysis:
        """
        Propose 3 actions pour diversifier le portefeuille (analyse MARKET + Gemini).

        Les suggestions enrichies (all_asset_id) sont stockées dans ``recommendations``.
        """
        logger.info(f"Début suggestion diversification IA pour {user.username}")

        analysis = AIAnalysis.objects.create(
            user=user,
            analysis_type=AIAnalysis.AnalysisType.MARKET,
            status=AIAnalysis.AnalysisStatus.PROCESSING,
            prompt="",
        )

        try:
            diversify_data = self._prepare_diversify_data(user)
            prompt = format_diversify_prompt(diversify_data)
            analysis.prompt = prompt
            analysis.save(update_fields=["prompt"])

            result = self.gemini_service.generate_analysis(prompt)

            if result["success"]:
                self._save_diversification_results(analysis, result)
                analysis.mark_as_completed()
                logger.info(f"Suggestion diversification terminée pour {user.username}")
            else:
                analysis.mark_as_failed(result["error"])
                logger.error(f"Échec diversification: {result['error']}")

        except Exception as e:
            error_msg = f"Erreur lors de la suggestion diversification: {str(e)}"
            logger.exception(error_msg)
            analysis.mark_as_failed(error_msg)

        return analysis

    def _prepare_diversify_data(self, user: User) -> Dict:
        """Prépare le contexte portefeuille pour le prompt de diversification."""
        positions = (
            Position.objects.filter(user=user, is_open=True)
            .select_related("all_asset")
            .order_by("-quantity")
        )

        if not positions.exists():
            positions_detailed = "Aucune position ouverte — l'utilisateur part d'un portefeuille vide ou non synchronisé."
            sectors_and_industries_held = "Aucune exposition sectorielle connue."
            total_position_value = "0.00"
            dominant_currency = "EUR"
            num_positions = 0
            return {
                "num_positions": num_positions,
                "total_position_value": total_position_value,
                "dominant_currency": dominant_currency,
                "positions_detailed": positions_detailed,
                "sectors_and_industries_held": sectors_and_industries_held,
            }

        total_value = 0.0
        currency_counts: Dict[str, float] = {}
        lines: List[str] = []
        sectors_seen = set()
        industries_seen = set()

        for pos in positions:
            aa = pos.all_asset
            sym = aa.symbol if aa else "Unknown"
            name = (aa.name if aa else "") or ""
            sector = (getattr(aa, "sector", None) or "").strip() if aa else ""
            industry = (getattr(aa, "industry", None) or "").strip() if aa else ""
            if sector:
                sectors_seen.add(sector)
            if industry:
                industries_seen.add(industry)

            px = float(pos.current_price or pos.entry_price or 0)
            qty = float(pos.quantity or 0)
            line_value = px * qty
            total_value += line_value

            cur = (aa.currency if aa else None) or "EUR"
            currency_counts[cur] = currency_counts.get(cur, 0.0) + line_value

        dominant_currency = max(currency_counts, key=currency_counts.get) if currency_counts else "EUR"

        for pos in positions:
            aa = pos.all_asset
            sym = aa.symbol if aa else "Unknown"
            name = (aa.name if aa else "") or ""
            sector = (getattr(aa, "sector", None) or "").strip() if aa else ""
            industry = (getattr(aa, "industry", None) or "").strip() if aa else ""
            px = float(pos.current_price or pos.entry_price or 0)
            qty = float(pos.quantity or 0)
            line_value = px * qty
            pct = (line_value / total_value * 100.0) if total_value > 0 else 0.0
            yahoo = (aa.symbole_yahoo if aa else "") or ""
            lines.append(
                f"- {sym} (Yahoo: {yahoo}) | {name or '—'} | secteur: {sector or '—'} | "
                f"industrie: {industry or '—'} | valeur ~{line_value:.2f} ({pct:.1f}% du portefeuille)"
            )

        positions_detailed = "\n".join(lines) if lines else "—"

        si_lines = []
        if sectors_seen:
            si_lines.append("Secteurs: " + ", ".join(sorted(sectors_seen)))
        if industries_seen:
            si_lines.append("Industries: " + ", ".join(sorted(industries_seen)))
        sectors_and_industries_held = "\n".join(si_lines) if si_lines else "Non renseigné en base — déduire à partir des noms/symboles."

        return {
            "num_positions": positions.count(),
            "total_position_value": f"{total_value:.2f}",
            "dominant_currency": dominant_currency,
            "positions_detailed": positions_detailed,
            "sectors_and_industries_held": sectors_and_industries_held,
        }

    def _find_all_asset_by_yahoo_symbol(self, yahoo_symbol: str) -> Optional[AllAssets]:
        """Résout un ticker Yahoo vers un AllAssets du catalogue (hors statuts invalides)."""
        if not yahoo_symbol or not isinstance(yahoo_symbol, str):
            return None
        y = yahoo_symbol.strip()
        if not y or y in ("Not_searched", "not_found", "manual"):
            return None
        invalid = ["Not_searched", "not_found", "manual", ""]
        qs = AllAssets.objects.exclude(symbole_yahoo__in=invalid).filter(symbole_yahoo__iexact=y)
        found = qs.first()
        if found:
            return found
        # Parfois l'IA renvoie le symbole broker (BASE:MIC) : tenter le symbole exact
        return (
            AllAssets.objects.exclude(symbole_yahoo__in=invalid)
            .filter(symbol__iexact=y)
            .first()
        )

    def _save_diversification_results(self, analysis: AIAnalysis, result: Dict):
        """Sauvegarde la réponse JSON diversification (suggestions + macro)."""
        analysis.response = result["response"]
        analysis.metadata = result.get("metadata") or {}

        parsed = result.get("parsed_data") or {}
        suggestions = parsed.get("suggestions")

        enriched: List[Dict] = []
        if isinstance(suggestions, list):
            for raw in suggestions:
                if not isinstance(raw, dict):
                    continue
                row = dict(raw)
                yahoo = (row.get("yahoo_symbol") or row.get("symbol") or "").strip()
                aa = self._find_all_asset_by_yahoo_symbol(yahoo)
                row["all_asset_id"] = aa.id if aa else None
                row["tradable"] = bool(aa)
                row["broker_symbol"] = aa.symbol if aa else None
                enriched.append(row)

        analysis.summary = parsed.get("summary", "") or ""
        analysis.recommendations = enriched
        analysis.insights = {
            "macro_context": parsed.get("macro_context", ""),
            "diversify_suggestions": enriched,
        }
        analysis.risks = []
        analysis.opportunities = []

        confs = [
            float(x["confidence"])
            for x in enriched
            if isinstance(x.get("confidence"), (int, float))
        ]
        if confs:
            analysis.confidence_score = sum(confs) / len(confs)
        elif parsed.get("confidence_score") is not None:
            try:
                analysis.confidence_score = float(parsed["confidence_score"])
            except (TypeError, ValueError):
                analysis.confidence_score = None
        else:
            analysis.confidence_score = None

        analysis.save()

    def suggest_sell(self, user: User) -> AIAnalysis:
        """
        Propose des actions à vendre du portefeuille (analyse MARKET + Gemini).

        Les suggestions de vente sont stockées dans ``recommendations``.
        """
        logger.info(f"Début suggestion vente IA pour {user.username}")

        analysis = AIAnalysis.objects.create(
            user=user,
            analysis_type=AIAnalysis.AnalysisType.MARKET,
            status=AIAnalysis.AnalysisStatus.PROCESSING,
            prompt="",
        )

        try:
            sell_data = self._prepare_sell_data(user)
            prompt = format_sell_suggestions_prompt(sell_data)
            analysis.prompt = prompt
            analysis.save(update_fields=["prompt"])

            result = self.gemini_service.generate_analysis(prompt)

            if result["success"]:
                self._save_sell_results(analysis, result)
                analysis.mark_as_completed()
                logger.info(f"Suggestion vente terminée pour {user.username}")
            else:
                analysis.mark_as_failed(result["error"])
                logger.error(f"Échec suggestion vente: {result['error']}")

        except Exception as e:
            error_msg = f"Erreur lors de la suggestion vente: {str(e)}"
            logger.exception(error_msg)
            analysis.mark_as_failed(error_msg)

        return analysis

    def _prepare_sell_data(self, user: User) -> Dict:
        """Prépare le contexte portefeuille pour le prompt de suggestion de vente."""
        positions = (
            Position.objects.filter(user=user, is_open=True)
            .select_related("all_asset")
            .order_by("-quantity")
        )

        if not positions.exists():
            return {
                "num_positions": 0,
                "total_position_value": "0.00",
                "dominant_currency": "EUR",
                "positions_detailed": "Aucune position ouverte — rien à vendre.",
            }

        total_value = 0.0
        currency_counts: Dict[str, float] = {}
        lines: List[str] = []

        for pos in positions:
            aa = pos.all_asset
            px = float(pos.current_price or pos.entry_price or 0)
            qty = float(pos.quantity or 0)
            line_value = px * qty
            total_value += line_value

            cur = (aa.currency if aa else None) or "EUR"
            currency_counts[cur] = currency_counts.get(cur, 0.0) + line_value

        dominant_currency = max(currency_counts, key=currency_counts.get) if currency_counts else "EUR"

        for pos in positions:
            aa = pos.all_asset
            sym = aa.symbol if aa else "Unknown"
            name = (aa.name if aa else "") or ""
            sector = (getattr(aa, "sector", None) or "").strip() if aa else ""
            industry = (getattr(aa, "industry", None) or "").strip() if aa else ""
            yahoo = (aa.symbole_yahoo if aa else "") or ""
            
            entry_px = float(pos.entry_price or 0)
            current_px = float(pos.current_price or entry_px or 0)
            qty = float(pos.quantity or 0)
            line_value = current_px * qty
            pct = (line_value / total_value * 100.0) if total_value > 0 else 0.0
            
            pnl_value = (current_px - entry_px) * qty if entry_px > 0 else 0
            pnl_pct = ((current_px - entry_px) / entry_px * 100.0) if entry_px > 0 else 0
            pnl_sign = "+" if pnl_value >= 0 else ""
            
            lines.append(
                f"- {sym} (Yahoo: {yahoo}) | {name or '—'} | secteur: {sector or '—'} | "
                f"industrie: {industry or '—'} | qté: {qty:.2f} | "
                f"prix entrée: {entry_px:.2f} | prix actuel: {current_px:.2f} | "
                f"PnL: {pnl_sign}{pnl_value:.2f} ({pnl_sign}{pnl_pct:.1f}%) | "
                f"valeur: ~{line_value:.2f} ({pct:.1f}% du portefeuille)"
            )

        positions_detailed = "\n".join(lines) if lines else "—"

        return {
            "num_positions": positions.count(),
            "total_position_value": f"{total_value:.2f}",
            "dominant_currency": dominant_currency,
            "positions_detailed": positions_detailed,
        }

    def _save_sell_results(self, analysis: AIAnalysis, result: Dict):
        """Sauvegarde la réponse JSON suggestions de vente."""
        analysis.response = result["response"]
        analysis.metadata = result.get("metadata") or {}

        parsed = result.get("parsed_data") or {}
        suggestions = parsed.get("suggestions")

        enriched: List[Dict] = []
        if isinstance(suggestions, list):
            for raw in suggestions:
                if not isinstance(raw, dict):
                    continue
                row = dict(raw)
                yahoo = (row.get("yahoo_symbol") or row.get("symbol") or "").strip()
                aa = self._find_all_asset_by_yahoo_symbol(yahoo)
                row["all_asset_id"] = aa.id if aa else None
                row["tradable"] = bool(aa)
                row["broker_symbol"] = aa.symbol if aa else None
                enriched.append(row)

        analysis.summary = parsed.get("summary", "") or ""
        analysis.recommendations = enriched
        analysis.insights = {
            "macro_context": parsed.get("macro_context", ""),
            "sell_suggestions": enriched,
        }
        analysis.risks = []
        analysis.opportunities = []

        confs = [
            float(x["confidence"])
            for x in enriched
            if isinstance(x.get("confidence"), (int, float))
        ]
        if confs:
            analysis.confidence_score = sum(confs) / len(confs)
        elif parsed.get("confidence_score") is not None:
            try:
                analysis.confidence_score = float(parsed["confidence_score"])
            except (TypeError, ValueError):
                analysis.confidence_score = None
        else:
            analysis.confidence_score = None

        analysis.save()
    
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
