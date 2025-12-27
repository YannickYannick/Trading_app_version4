"""
Modèles de base et abstraits.
"""
from django.db import models


class TimeStampedModel(models.Model):
    """Modèle abstrait avec timestamps de création et modification."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

