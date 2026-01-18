"""
Modèles liés aux stratégies de trading.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .base import TimeStampedModel


class AlgorithmSchema(TimeStampedModel):
    """Schéma définissant la structure d'un type d'algorithme."""
    algorithm_type = models.CharField(max_length=50, unique=True, help_text="Type d'algorithme (threshold, rsi, etc.)")
    name = models.CharField(max_length=100, help_text="Nom affiché de l'algorithme")
    description = models.TextField(blank=True, help_text="Description de l'algorithme")
    
    class Meta:
        ordering = ['algorithm_type']
        verbose_name = 'Algorithm Schema'
        verbose_name_plural = 'Algorithm Schemas'
    
    def __str__(self):
        return f"{self.name} ({self.algorithm_type})"


class AlgorithmParameterDefinition(TimeStampedModel):
    """Définition d'un paramètre attendu pour un schéma d'algorithme."""
    schema = models.ForeignKey(
        AlgorithmSchema,
        on_delete=models.CASCADE,
        related_name='parameter_definitions'
    )
    key = models.CharField(max_length=100, help_text="Clé du paramètre")
    param_type = models.CharField(
        max_length=10,
        choices=[
            ('int', 'Integer'),
            ('float', 'Float'),
            ('str', 'String'),
            ('bool', 'Boolean'),
        ],
        help_text="Type de données du paramètre"
    )
    default_value = models.TextField(blank=True, help_text="Valeur par défaut")
    required = models.BooleanField(default=True, help_text="Paramètre obligatoire")
    description = models.CharField(max_length=255, blank=True, help_text="Description du paramètre")
    min_value = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True, help_text="Valeur minimale")
    max_value = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True, help_text="Valeur maximale")
    
    class Meta:
        unique_together = ['schema', 'key']
        ordering = ['key']
        verbose_name = 'Algorithm Parameter Definition'
        verbose_name_plural = 'Algorithm Parameter Definitions'
    
    def __str__(self):
        return f"{self.schema.algorithm_type}.{self.key} ({self.param_type})"


class AlgorithmParameter(TimeStampedModel):
    """Paramètre d'un algorithme pour une stratégie."""
    strategy = models.ForeignKey(
        'Strategy',
        on_delete=models.CASCADE,
        related_name='algorithm_parameters'
    )
    key = models.CharField(max_length=100, help_text="Clé du paramètre")
    value = models.TextField(help_text="Valeur du paramètre (stockée en string)")
    param_type = models.CharField(
        max_length=10,
        choices=[
            ('int', 'Integer'),
            ('float', 'Float'),
            ('str', 'String'),
            ('bool', 'Boolean'),
        ],
        help_text="Type de données du paramètre"
    )
    description = models.CharField(max_length=255, blank=True, help_text="Description du paramètre")
    
    class Meta:
        unique_together = ['strategy', 'key']
        ordering = ['key']
        verbose_name = 'Algorithm Parameter'
        verbose_name_plural = 'Algorithm Parameters'
        indexes = [
            models.Index(fields=['strategy', 'key']),
        ]
    
    def __str__(self):
        return f"{self.strategy.name}.{self.key} = {self.value}"
    
    def get_value(self):
        """Convertit la valeur selon le param_type."""
        if self.param_type == 'int':
            return int(self.value)
        elif self.param_type == 'float':
            return float(self.value)
        elif self.param_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        else:
            return self.value


class Strategy(TimeStampedModel):
    """Stratégie de trading."""
    
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Faible'
        MEDIUM = 'MEDIUM', 'Moyen'
        HIGH = 'HIGH', 'Élevé'
    
    class AlgorithmType(models.TextChoices):
        THRESHOLD = 'threshold', 'Threshold'
        MA_CROSSOVER = 'ma_crossover', 'Moving Average Crossover'
        RSI = 'rsi', 'RSI'
        BOLLINGER = 'bollinger', 'Bollinger Bands'
        MACD = 'macd', 'MACD'
        GRID = 'grid', 'Grid Trading'
    
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='strategies'
    )
    
    # Asset cible de la stratégie (obligatoire pour nouvelles stratégies)
    # Note: nullable temporairement pour permettre la migration des stratégies existantes
    all_asset = models.ForeignKey(
        'AllAssets',
        on_delete=models.CASCADE,
        related_name='strategies',
        null=True,
        blank=False,  # Obligatoire dans le formulaire
        help_text="Asset cible que cette stratégie trade"
    )
    
    # Compte broker pour exécuter cette stratégie
    broker_account = models.ForeignKey(
        'BrokerAccount',
        on_delete=models.SET_NULL,
        null=True, # Garder null=True pour SET_NULL, mais blank=False pour le rendre obligatoire
        blank=False,
        related_name='strategies',
        help_text="Compte broker pour exécuter cette stratégie"
    )
    
    # Asset Saxo spécifique (optionnel, pour compatibilité)
    asset = models.ForeignKey(
        'Asset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='strategies',
        help_text="Asset Saxo spécifique (optionnel)"
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Configuration
    algorithm_type = models.CharField(
        max_length=20,
        choices=AlgorithmType.choices,
        null=True,
        blank=True,
        help_text="Type d'algorithme de trading"
    )
    execution_mode = models.CharField(
        max_length=20,
        choices=[
            ('simulation', 'Simulation'),
            ('paper_trading', 'Paper Trading'),
            ('live_trading', 'Trading Réel'),
        ],
        default='live_trading',
        help_text="Mode d'exécution de la stratégie"
    )
    risk_level = models.CharField(
        max_length=10, choices=RiskLevel.choices, default=RiskLevel.MEDIUM
    )
    
    # Quantité et budget
    min_quantity = models.DecimalField(
        max_digits=20, decimal_places=10, default=0, null=False, blank=False,
        help_text="Quantité minimale d'achat"
    )
    max_quantity = models.DecimalField(
        max_digits=20, decimal_places=10, default=1, null=False, blank=False,
        help_text="Quantité maximale d'achat"
    )
    budget = models.DecimalField(
        max_digits=20, decimal_places=2, default=1000, null=False, blank=False,
        help_text="Budget alloué à cette stratégie"
    )
    
    # Paramètres (JSONField conservé pour compatibilité backward)
    parameters = models.JSONField(default=dict, blank=True, help_text="Paramètres (ancien système - utilisé en fallback)")
    
    # Fréquence et portfolio
    check_frequency = models.IntegerField(
        default=45,
        help_text="Fréquence de vérification en minutes"
    )
    portfolio_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        default=0,
        help_text="Quantité actuellement détenue en portefeuille"
    )
    
    # Statut
    is_active = models.BooleanField(
        default=True,
        help_text="Stratégie active"
    )
    is_automated = models.BooleanField(
        default=True,
        help_text="Trading automatique activé"
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Strategy'
        verbose_name_plural = 'Strategies'
        indexes = [
            models.Index(fields=['all_asset', 'is_active']),
        ]
    
    def __str__(self):
        if self.all_asset:
            return f"{self.name} ({self.all_asset.symbol})"
        return self.name
    
    def get_parameters_dict(self):
        """Retourne les paramètres, en priorité depuis AlgorithmParameter, fallback vers JSONField."""
        # Essayer le nouveau système (AlgorithmParameter)
        new_params = {
            param.key: param.get_value()
            for param in self.algorithm_parameters.all()
        }
        
        if new_params:
            return new_params
        
        # Fallback vers l'ancien système (JSONField)
        return self.parameters or {}
    
    def set_parameter(self, key, value, param_type, description=''):
        """Crée ou met à jour un paramètre."""
        param, created = AlgorithmParameter.objects.update_or_create(
            strategy=self,
            key=key,
            defaults={
                'value': str(value),
                'param_type': param_type,
                'description': description,
            }
        )
        return param
    
    def get_parameter(self, key, default=None):
        """Récupère un paramètre avec conversion de type."""
        try:
            param = self.algorithm_parameters.get(key=key)
            return param.get_value()
        except AlgorithmParameter.DoesNotExist:
            # Fallback vers JSONField
            return self.parameters.get(key, default)
    
    def validate_parameters(self):
        """Valide les paramètres selon le schéma."""
        errors = []
        
        if not self.algorithm_type:
            return errors  # Pas de validation si pas d'algorithme
        
        try:
            schema = AlgorithmSchema.objects.get(algorithm_type=self.algorithm_type)
        except AlgorithmSchema.DoesNotExist:
            return errors  # Pas de schéma, pas de validation
        
        # Récupérer les définitions
        definitions = schema.parameter_definitions.all()
        param_dict = self.get_parameters_dict()
        
        for definition in definitions:
            key = definition.key
            
            # Vérifier si le paramètre est requis
            if definition.required and key not in param_dict:
                errors.append(f"Paramètre requis manquant: {key}")
                continue
            
            # Vérifier le type
            if key in param_dict:
                value = param_dict[key]
                
                # Conversion et validation du type
                try:
                    if definition.param_type == 'int':
                        value = int(value)
                    elif definition.param_type == 'float':
                        value = float(value)
                    elif definition.param_type == 'bool':
                        value = bool(value) if not isinstance(value, str) else value.lower() in ('true', '1', 'yes', 'on')
                    # str ne nécessite pas de conversion
                    
                    # Vérifier min/max pour les valeurs numériques
                    if definition.param_type in ('int', 'float') and isinstance(value, (int, float)):
                        if definition.min_value is not None and value < float(definition.min_value):
                            errors.append(f"{key}: valeur {value} inférieure au minimum {definition.min_value}")
                        if definition.max_value is not None and value > float(definition.max_value):
                            errors.append(f"{key}: valeur {value} supérieure au maximum {definition.max_value}")
                
                except (ValueError, TypeError) as e:
                    errors.append(f"{key}: erreur de conversion de type ({e})")
        
        return errors
    
    def initialize_default_parameters(self):
        """Initialise les paramètres par défaut depuis le schéma."""
        if not self.algorithm_type:
            return
        
        try:
            schema = AlgorithmSchema.objects.get(algorithm_type=self.algorithm_type)
        except AlgorithmSchema.DoesNotExist:
            return  # Pas de schéma, rien à faire
        
        for definition in schema.parameter_definitions.all():
            # Vérifier si le paramètre existe déjà
            if not self.algorithm_parameters.filter(key=definition.key).exists():
                self.set_parameter(
                    key=definition.key,
                    value=definition.default_value or '',
                    param_type=definition.param_type,
                    description=definition.description
                )
    
    def get_algorithm_instance(self):
        """Retourne une instance de l'algorithme avec les paramètres."""
        if not self.algorithm_type:
            return None
        
        try:
            from apps.trading.algorithms import AlgorithmFactory
            parameters = self.get_parameters_dict()
            return AlgorithmFactory.create_algorithm(self.algorithm_type, parameters, self)
        except ImportError:
            return None
        except Exception as e:
            # Log l'erreur mais ne bloque pas
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de la création de l'algorithme: {e}")
            return None


class StrategyPerformance(TimeStampedModel):
    """Performance journalière d'une stratégie."""
    strategy = models.ForeignKey(
        Strategy, on_delete=models.CASCADE, related_name='performances'
    )
    date = models.DateField()
    
    # Métriques
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    
    gross_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    fees = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    net_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['strategy', 'date']
        ordering = ['-date']
        verbose_name = 'Strategy Performance'
        verbose_name_plural = 'Strategy Performances'
    
    def __str__(self):
        return f"{self.strategy.name} - {self.date}"
    
    @property
    def win_rate(self):
        """Calcule le taux de réussite."""
        if self.total_trades == 0:
            return 0
        return (self.winning_trades / self.total_trades) * 100

