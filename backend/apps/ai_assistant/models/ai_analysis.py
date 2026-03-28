"""
Modèles pour les analyses IA de trading.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class AIAnalysis(models.Model):
    """
    Analyse IA d'une stratégie ou d'un portefeuille.
    Stocke les recommandations, insights et prédictions générées par l'IA.
    """
    
    class AnalysisType(models.TextChoices):
        STRATEGY = 'STRATEGY', 'Analyse de stratégie'
        PORTFOLIO = 'PORTFOLIO', 'Analyse de portefeuille'
        ASSET = 'ASSET', 'Analyse d\'actif'
        MARKET = 'MARKET', 'Analyse de marché'
    
    class AnalysisStatus(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        PROCESSING = 'PROCESSING', 'En cours'
        COMPLETED = 'COMPLETED', 'Terminée'
        FAILED = 'FAILED', 'Échouée'
    
    # Métadonnées
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_analyses',
        help_text="Utilisateur propriétaire de l'analyse"
    )
    
    analysis_type = models.CharField(
        max_length=20,
        choices=AnalysisType.choices,
        help_text="Type d'analyse effectuée"
    )
    
    status = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
        help_text="Statut de l'analyse"
    )
    
    # Relations optionnelles selon le type
    strategy = models.ForeignKey(
        'trading.Strategy',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_analyses',
        help_text="Stratégie analysée (si analysis_type=STRATEGY)"
    )
    
    all_asset = models.ForeignKey(
        'trading.AllAssets',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_analyses',
        help_text="Actif analysé (si analysis_type=ASSET)"
    )
    
    # Données de l'analyse
    prompt = models.TextField(
        help_text="Prompt envoyé à l'IA"
    )
    
    response = models.TextField(
        blank=True,
        help_text="Réponse brute de l'IA"
    )
    
    # Résultats structurés (JSON)
    summary = models.TextField(
        blank=True,
        help_text="Résumé de l'analyse"
    )
    
    recommendations = models.JSONField(
        default=list,
        help_text="Liste de recommandations structurées"
    )
    
    insights = models.JSONField(
        default=dict,
        help_text="Insights clés extraits (métriques, tendances, etc.)"
    )
    
    risks = models.JSONField(
        default=list,
        help_text="Risques identifiés"
    )
    
    opportunities = models.JSONField(
        default=list,
        help_text="Opportunités identifiées"
    )
    
    # Métadonnées de qualité
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score de confiance de l'IA (0-100)"
    )
    
    metadata = models.JSONField(
        default=dict,
        help_text="Métadonnées additionnelles (version modèle, tokens utilisés, etc.)"
    )
    
    # Erreur (si échec)
    error_message = models.TextField(
        blank=True,
        help_text="Message d'erreur en cas d'échec"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date de dernière modification"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de complétion de l'analyse"
    )
    
    # Flags
    is_daily_report = models.BooleanField(
        default=False,
        help_text="True si généré par le rapport quotidien automatique"
    )
    
    is_archived = models.BooleanField(
        default=False,
        help_text="True si l'analyse est archivée"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI Analysis'
        verbose_name_plural = 'AI Analyses'
        indexes = [
            models.Index(fields=['user', 'analysis_type', '-created_at']),
            models.Index(fields=['strategy', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['is_daily_report', '-created_at']),
        ]
    
    def __str__(self):
        type_label = self.get_analysis_type_display()
        if self.strategy:
            return f"{type_label} - {self.strategy.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
        elif self.all_asset:
            return f"{type_label} - {self.all_asset.symbol} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
        else:
            return f"{type_label} - Portfolio ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    def get_scope_description(self):
        """Retourne une description du scope de l'analyse."""
        if self.analysis_type == self.AnalysisType.STRATEGY and self.strategy:
            return f"Stratégie: {self.strategy.name}"
        elif self.analysis_type == self.AnalysisType.ASSET and self.all_asset:
            return f"Actif: {self.all_asset.symbol}"
        elif self.analysis_type == self.AnalysisType.PORTFOLIO:
            return "Portefeuille complet"
        else:
            return "Analyse de marché"
    
    def mark_as_completed(self):
        """Marque l'analyse comme terminée."""
        from django.utils import timezone
        self.status = self.AnalysisStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    def mark_as_failed(self, error_message):
        """Marque l'analyse comme échouée."""
        from django.utils import timezone
        self.status = self.AnalysisStatus.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
