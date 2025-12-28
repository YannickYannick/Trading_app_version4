"""
Health check endpoint for testing backend connectivity.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint.
    
    GET /api/health/
    
    Returns:
        {
            "status": "ok",
            "timestamp": "2024-12-27T10:00:00Z",
            "service": "trading-api"
        }
    """
    return Response({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'service': 'trading-api',
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    """
    Simple ping endpoint for connectivity testing.
    
    GET /api/ping/
    
    Returns:
        {
            "pong": true,
            "timestamp": "2024-12-27T10:00:00Z"
        }
    """
    return Response({
        'pong': True,
        'timestamp': timezone.now().isoformat(),
    }, status=status.HTTP_200_OK)

