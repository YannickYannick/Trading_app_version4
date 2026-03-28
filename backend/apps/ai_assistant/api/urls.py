"""
URL configuration for AI Assistant API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.ai_assistant.api.views import AIAnalysisViewSet

app_name = 'ai_assistant'

router = DefaultRouter()
router.register(r'analyses', AIAnalysisViewSet, basename='analysis')

urlpatterns = [
    path('', include(router.urls)),
]
