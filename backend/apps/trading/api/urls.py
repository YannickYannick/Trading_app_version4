"""
URLs de l'API REST Trading.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'assets', views.AssetViewSet, basename='asset')
router.register(r'positions', views.PositionViewSet, basename='position')
router.register(r'trades', views.TradeViewSet, basename='trade')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'strategies', views.StrategyViewSet, basename='strategy')
router.register(r'brokers', views.BrokerViewSet, basename='broker')
router.register(r'broker-accounts', views.BrokerAccountViewSet, basename='broker-account')

urlpatterns = [
    path('', include(router.urls)),
]

