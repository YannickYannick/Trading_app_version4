"""
Utilitaires pour les réponses API standardisées.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data: dict = None, message: str = None, status_code: int = status.HTTP_200_OK) -> Response:
    """
    Retourne une réponse de succès standardisée.
    
    Args:
        data: Données à retourner
        message: Message optionnel
        status_code: Code HTTP (défaut: 200)
        
    Returns:
        Response standardisée
    """
    response_data = {'success': True}
    if message:
        response_data['message'] = message
    if data:
        response_data.update(data)
    return Response(response_data, status=status_code)


def error_response(error: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict = None) -> Response:
    """
    Retourne une réponse d'erreur standardisée.
    
    Args:
        error: Message d'erreur
        status_code: Code HTTP (défaut: 400)
        details: Détails additionnels optionnels
        
    Returns:
        Response standardisée
    """
    response_data = {
        'success': False,
        'error': error
    }
    if details:
        response_data['details'] = details
    return Response(response_data, status=status_code)











