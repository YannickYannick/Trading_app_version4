"""
API views pour AI Assistant.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from apps.ai_assistant.models import AIAnalysis
from apps.ai_assistant.api.serializers import (
    AIAnalysisSerializer,
    AIAnalysisListSerializer,
    AIAnalysisCreateSerializer,
    AIAnalysisQuickSerializer
)
from apps.ai_assistant.services.trading_analysis_service import TradingAnalysisService
from apps.trading.models import Strategy, AllAssets

logger = logging.getLogger('ai_assistant')


class AIAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les analyses IA.
    
    Liste et détaille les analyses existantes.
    Permet de créer de nouvelles analyses via des actions custom.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'list':
            return AIAnalysisListSerializer
        elif self.action == 'latest':
            return AIAnalysisQuickSerializer
        return AIAnalysisSerializer
    
    def get_queryset(self):
        """Retourne les analyses de l'utilisateur connecté."""
        user = self.request.user
        queryset = AIAnalysis.objects.filter(user=user)
        
        # Filtres
        analysis_type = self.request.query_params.get('analysis_type')
        if analysis_type:
            queryset = queryset.filter(analysis_type=analysis_type)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        strategy_id = self.request.query_params.get('strategy')
        if strategy_id:
            queryset = queryset.filter(strategy_id=strategy_id)
        
        is_daily = self.request.query_params.get('is_daily_report')
        if is_daily is not None:
            queryset = queryset.filter(is_daily_report=is_daily.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'], url_path='analyze-strategy')
    def analyze_strategy(self, request):
        """
        Analyse une stratégie spécifique.
        
        POST /api/ai/analyses/analyze-strategy/
        Body: {"strategy_id": 123, "force_new": false}
        """
        serializer = AIAnalysisCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        strategy_id = serializer.validated_data.get('strategy_id')
        force_new = serializer.validated_data.get('force_new', False)
        
        if not strategy_id:
            return Response(
                {'error': 'strategy_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que la stratégie existe et appartient à l'utilisateur
        try:
            strategy = Strategy.objects.get(id=strategy_id, user=request.user)
        except Strategy.DoesNotExist:
            return Response(
                {'error': 'Stratégie non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier s'il existe une analyse récente (moins de 1h)
        if not force_new:
            one_hour_ago = timezone.now() - timedelta(hours=1)
            recent_analysis = AIAnalysis.objects.filter(
                user=request.user,
                strategy=strategy,
                status=AIAnalysis.AnalysisStatus.COMPLETED,
                created_at__gte=one_hour_ago
            ).first()
            
            if recent_analysis:
                return Response(
                    {
                        'message': 'Une analyse récente existe déjà',
                        'analysis': AIAnalysisSerializer(recent_analysis).data
                    },
                    status=status.HTTP_200_OK
                )
        
        # Créer l'analyse
        try:
            analysis_service = TradingAnalysisService()
            analysis = analysis_service.analyze_strategy(strategy, request.user)
            
            return Response(
                AIAnalysisSerializer(analysis).data,
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de stratégie: {e}")
            return Response(
                {'error': f'Erreur lors de l\'analyse: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='analyze-portfolio')
    def analyze_portfolio(self, request):
        """
        Analyse le portefeuille complet de l'utilisateur.
        
        POST /api/ai/analyses/analyze-portfolio/
        Body: {"force_new": false}
        """
        serializer = AIAnalysisCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        force_new = serializer.validated_data.get('force_new', False)
        
        # Vérifier s'il existe une analyse récente (moins de 1h)
        if not force_new:
            one_hour_ago = timezone.now() - timedelta(hours=1)
            recent_analysis = AIAnalysis.objects.filter(
                user=request.user,
                analysis_type=AIAnalysis.AnalysisType.PORTFOLIO,
                status=AIAnalysis.AnalysisStatus.COMPLETED,
                created_at__gte=one_hour_ago
            ).first()
            
            if recent_analysis:
                return Response(
                    {
                        'message': 'Une analyse récente existe déjà',
                        'analysis': AIAnalysisSerializer(recent_analysis).data
                    },
                    status=status.HTTP_200_OK
                )
        
        # Créer l'analyse
        try:
            analysis_service = TradingAnalysisService()
            analysis = analysis_service.analyze_portfolio(request.user)
            
            return Response(
                AIAnalysisSerializer(analysis).data,
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de portefeuille: {e}")
            return Response(
                {'error': f'Erreur lors de l\'analyse: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """
        Retourne les dernières analyses par type.
        
        GET /api/ai/analyses/latest/?analysis_type=STRATEGY&strategy=123
        GET /api/ai/analyses/latest/?analysis_type=PORTFOLIO
        """
        analysis_type = request.query_params.get('analysis_type')
        strategy_id = request.query_params.get('strategy')
        
        if not analysis_type:
            return Response(
                {'error': 'analysis_type est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Construire la requête
        queryset = AIAnalysis.objects.filter(
            user=request.user,
            analysis_type=analysis_type,
            status=AIAnalysis.AnalysisStatus.COMPLETED
        )
        
        if strategy_id:
            queryset = queryset.filter(strategy_id=strategy_id)
        
        # Récupérer la plus récente
        latest_analysis = queryset.order_by('-created_at').first()
        
        if not latest_analysis:
            return Response(
                {'message': 'Aucune analyse trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AIAnalysisQuickSerializer(latest_analysis)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        """
        Archive une analyse.
        
        POST /api/ai/analyses/{id}/archive/
        """
        analysis = self.get_object()
        
        if analysis.user != request.user:
            return Response(
                {'error': 'Vous n\'avez pas la permission'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        analysis.is_archived = True
        analysis.save(update_fields=['is_archived'])
        
        return Response(
            {'message': 'Analyse archivée avec succès'},
            status=status.HTTP_200_OK
        )
