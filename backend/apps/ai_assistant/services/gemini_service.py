"""
Service d'intégration avec l'API Google Gemini.
"""
import logging
import time
import json
from typing import Dict, Optional
from decouple import config
from google import genai
from django.conf import settings

logger = logging.getLogger('ai_assistant')


class GeminiAIService:
    """
    Service pour interagir avec l'API Google Gemini.
    Gère l'authentification, les requêtes, et le parsing des réponses.
    """
    
    def __init__(self):
        """Initialise le service Gemini AI."""
        self.api_key = config('GEMINI_API_KEY', default='')
        if not self.api_key:
            logger.warning("GEMINI_API_KEY non configurée. Le service IA sera désactivé.")
            self.enabled = False
        else:
            self.enabled = True
            self.client = genai.Client(api_key=self.api_key)
            
            # Configuration du modèle
            self.model_name = config('GEMINI_MODEL', default='gemini-2.5-flash')
            
            # Configuration de génération
            self.generation_config = {
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
            
            logger.info(f"GeminiAIService initialisé avec le modèle {self.model_name}")
    
    def is_enabled(self) -> bool:
        """Vérifie si le service IA est activé."""
        return self.enabled
    
    def generate_analysis(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Dict:
        """
        Génère une analyse à partir d'un prompt.
        
        Args:
            prompt: Prompt à envoyer à l'IA
            max_retries: Nombre maximum de tentatives en cas d'erreur
            retry_delay: Délai entre les tentatives (secondes)
        
        Returns:
            Dict contenant:
                - success: bool
                - response: str (réponse brute)
                - parsed_data: dict (réponse parsée en JSON)
                - metadata: dict (métadonnées de la requête)
                - error: str (message d'erreur si échec)
        
        Raises:
            Exception: Si le service n'est pas activé
        """
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'Service IA non activé. GEMINI_API_KEY manquante.',
                'response': '',
                'parsed_data': {},
                'metadata': {}
            }
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Génération d'analyse (tentative {attempt + 1}/{max_retries})")
                
                # Générer la réponse
                start_time = time.time()
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                elapsed_time = time.time() - start_time
                
                # Extraire le texte de la réponse
                response_text = response.text
                
                # Métadonnées
                metadata = {
                    'model': self.model_name,
                    'elapsed_time': elapsed_time,
                    'attempt': attempt + 1,
                    'prompt_length': len(prompt),
                    'response_length': len(response_text),
                }
                
                # Essayer de parser en JSON
                parsed_data = self._parse_json_response(response_text)
                
                logger.info(f"Analyse générée avec succès en {elapsed_time:.2f}s")
                
                return {
                    'success': True,
                    'response': response_text,
                    'parsed_data': parsed_data,
                    'metadata': metadata,
                    'error': ''
                }
                
            except Exception as e:
                error_msg = f"Erreur lors de la génération (tentative {attempt + 1}): {str(e)}"
                logger.error(error_msg)
                
                if attempt < max_retries - 1:
                    logger.info(f"Nouvelle tentative dans {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                else:
                    return {
                        'success': False,
                        'error': error_msg,
                        'response': '',
                        'parsed_data': {},
                        'metadata': {'attempts': max_retries}
                    }
        
        return {
            'success': False,
            'error': 'Nombre maximum de tentatives atteint',
            'response': '',
            'parsed_data': {},
            'metadata': {'attempts': max_retries}
        }
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Parse la réponse de l'IA en JSON.
        
        Args:
            response_text: Texte de la réponse
        
        Returns:
            Dict: Données parsées ou {} si échec
        """
        try:
            # Essayer de parser directement
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Essayer d'extraire le JSON d'un bloc de code
            try:
                # Chercher un bloc JSON entre ```json et ```
                if '```json' in response_text:
                    start = response_text.find('```json') + 7
                    end = response_text.find('```', start)
                    json_text = response_text[start:end].strip()
                    return json.loads(json_text)
                
                # Chercher un bloc JSON entre { et }
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end > start:
                    json_text = response_text[start:end]
                    return json.loads(json_text)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Impossible de parser la réponse en JSON: {e}")
        
        return {}
    
    def test_connection(self) -> Dict:
        """
        Teste la connexion à l'API Gemini.
        
        Returns:
            Dict avec success: bool et message: str
        """
        if not self.is_enabled():
            return {
                'success': False,
                'message': 'Service IA non activé. GEMINI_API_KEY manquante.'
            }
        
        try:
            response = self.generate_analysis(
                prompt="Réponds simplement 'OK' si tu me reçois.",
                max_retries=1
            )
            
            if response['success']:
                return {
                    'success': True,
                    'message': f"Connexion réussie au modèle {self.model_name}"
                }
            else:
                return {
                    'success': False,
                    'message': f"Erreur: {response['error']}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Erreur de connexion: {str(e)}"
            }
