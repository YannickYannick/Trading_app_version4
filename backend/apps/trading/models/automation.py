"""
Modèles liés à l'automatisation des tâches.
"""
from django.db import models
from .base import TimeStampedModel


class ScheduledTask(TimeStampedModel):
    """Tâche planifiée."""
    
    class TaskType(models.TextChoices):
        SYNC_POSITIONS = 'SYNC_POSITIONS', 'Sync Positions'
        SYNC_TRADES = 'SYNC_TRADES', 'Sync Trades'
        SYNC_PRICES = 'SYNC_PRICES', 'Sync Prix'
        SYNC_ASSETS = 'SYNC_ASSETS', 'Sync Assets'
        REFRESH_TOKENS = 'REFRESH_TOKENS', 'Refresh Tokens'
        CUSTOM = 'CUSTOM', 'Personnalisée'
    
    class TriggerType(models.TextChoices):
        CRON = 'CRON', 'Cron'
        INTERVAL = 'INTERVAL', 'Intervalle'
        ONE_TIME = 'ONE_TIME', 'Une fois'
    
    name = models.CharField(max_length=100)
    task_type = models.CharField(max_length=30, choices=TaskType.choices)
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices)
    
    # Configuration du déclencheur
    cron_expression = models.CharField(
        max_length=100, blank=True,
        help_text="Ex: 0 */15 * * * (toutes les 15 min)"
    )
    interval_minutes = models.IntegerField(
        null=True, blank=True,
        help_text="Intervalle en minutes"
    )
    
    # Configuration de la tâche
    parameters = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Scheduled Task'
        verbose_name_plural = 'Scheduled Tasks'
    
    def __str__(self):
        return f"{self.name} ({self.task_type})"


class TaskExecutionLog(TimeStampedModel):
    """Log d'exécution d'une tâche."""
    
    class ExecutionStatus(models.TextChoices):
        RUNNING = 'RUNNING', 'En cours'
        SUCCESS = 'SUCCESS', 'Succès'
        FAILED = 'FAILED', 'Échec'
        CANCELLED = 'CANCELLED', 'Annulée'
    
    task = models.ForeignKey(
        ScheduledTask, on_delete=models.CASCADE, related_name='execution_logs'
    )
    status = models.CharField(
        max_length=20, choices=ExecutionStatus.choices
    )
    
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Task Execution Log'
        verbose_name_plural = 'Task Execution Logs'
    
    def __str__(self):
        return f"{self.task.name} - {self.started_at} ({self.status})"

