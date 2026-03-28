"""
Server-Sent Events (SSE) endpoint for streaming strategy execution updates.

This module provides real-time updates for strategy executions using SSE,
eliminating the need for polling.
"""
import json
import time
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from apps.trading.models import StrategyExecution
import logging

logger = logging.getLogger('trading.api.sse')
User = get_user_model()


@require_http_methods(["GET"])
@csrf_exempt
def strategy_execution_stream(request):
    """
    SSE endpoint for streaming new strategy executions in real-time.
    
    GET /api/strategy-executions/stream/?last_id=0&token=<jwt_token>
    
    Query Parameters:
        last_id (int): ID of the last execution received by the client
        token (str): JWT access token for authentication
        
    Returns:
        StreamingHttpResponse with text/event-stream content type
        
    Event Format:
        data: {"id": 1, "strategy_name": "BTC", "status": "completed", ...}
    """
    # Authentification via token JWT dans l'URL
    token_str = request.GET.get('token')
    
    if not token_str:
        # Fallback: vérifier si l'utilisateur est authentifié via session
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required. Provide token parameter.'}, status=401)
        user = request.user
    else:
        # Valider le token JWT
        try:
            token = AccessToken(token_str)
            user_id = token['user_id']
            user = User.objects.get(id=user_id)
        except (TokenError, User.DoesNotExist) as e:
            logger.warning(f"Invalid token in SSE request: {e}")
            return JsonResponse({'error': 'Invalid or expired token'}, status=401)
    
    last_id = int(request.GET.get('last_id', 0))
    
    logger.info(f"SSE connection opened for user {user.username}, last_id={last_id}")
    
    def event_stream():
        """Generator function that yields SSE events."""
        current_last_id = last_id
        heartbeat_counter = 0
        
        try:
            while True:
                # Récupérer les nouvelles exécutions depuis current_last_id
                new_executions = StrategyExecution.objects.filter(
                    strategy__user=user,
                    id__gt=current_last_id
                ).select_related('strategy').order_by('id')[:20]
                
                if new_executions.exists():
                    for execution in new_executions:
                        # Calculer la durée si l'exécution est terminée
                        duration = None
                        if execution.completed_at and execution.started_at:
                            duration = (execution.completed_at - execution.started_at).total_seconds()
                        
                        # Préparer les données de l'exécution
                        data = {
                            'id': execution.id,
                            'strategy': execution.strategy_id,
                            'strategy_id': execution.strategy_id,
                            'strategy_name': execution.strategy.name,
                            'status': execution.status,
                            'signal': execution.signal or 'NONE',
                            'signal_price': float(execution.signal_price) if execution.signal_price else None,
                            'signal_quantity': float(execution.signal_quantity) if execution.signal_quantity else None,
                            'started_at': execution.started_at.isoformat(),
                            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                            'duration': round(duration, 2) if duration else None,
                            'error': execution.error,
                            'output': execution.output
                        }
                        
                        # Envoyer l'événement SSE
                        yield f"data: {json.dumps(data)}\n\n"
                        current_last_id = execution.id
                        
                        logger.debug(f"Sent execution {execution.id} to user {user.username}")
                
                # Heartbeat toutes les 10 secondes pour garder la connexion active
                heartbeat_counter += 1
                if heartbeat_counter >= 10:
                    yield f": heartbeat\n\n"
                    heartbeat_counter = 0
                
                # Attendre 1 seconde avant la prochaine vérification
                time.sleep(1)
                
        except GeneratorExit:
            logger.info(f"SSE connection closed for user {user.username}")
        except Exception as e:
            logger.error(f"SSE error for user {user.username}: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    # Créer la réponse SSE
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    # Headers nécessaires pour SSE
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Pour nginx
    response['Connection'] = 'keep-alive'
    
    return response
