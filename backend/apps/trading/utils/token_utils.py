"""
Utilitaires pour la gestion des tokens OAuth2 et d'authentification.
"""
from datetime import datetime
from typing import Optional, Union


def parse_iso_datetime(value: Optional[Union[str, datetime]]) -> Optional[datetime]:
    """
    Parse ISO datetime string with various formats.
    
    Gère plusieurs formats ISO:
    - '2024-01-01T12:00:00Z' (UTC avec Z)
    - '2024-01-01T12:00:00+00:00' (UTC avec timezone)
    - '2024-01-01T12:00:00' (sans timezone)
    - datetime object (retourné tel quel)
    
    Args:
        value: Valeur à parser (string ISO, datetime, ou None)
        
    Returns:
        datetime object ou None si value est None
        
    Raises:
        ValueError: Si le format ne peut pas être parsé
    """
    if value is None:
        return None
    
    # Si c'est déjà un datetime, le retourner tel quel
    if isinstance(value, datetime):
        return value
    
    # Si c'est une string, essayer de la parser
    if isinstance(value, str):
        # Essayer avec timezone UTC (+00:00)
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Essayer sans le Z (format sans timezone)
        try:
            return datetime.fromisoformat(value.replace('Z', ''))
        except ValueError:
            pass
        
        # Dernière tentative avec le format standard
        try:
            return datetime.fromisoformat(value)
        except ValueError as e:
            raise ValueError(f"Impossible de parser la date ISO: {value}") from e
    
    raise TypeError(f"Type non supporté pour parse_iso_datetime: {type(value)}")


def format_token_expires_at(expires_at: Optional[Union[str, datetime]]) -> Optional[str]:
    """
    Formate un datetime en string ISO pour stockage.
    
    Args:
        expires_at: datetime ou string ISO
        
    Returns:
        String ISO format ou None
    """
    if expires_at is None:
        return None
    
    dt = parse_iso_datetime(expires_at)
    if dt:
        return dt.isoformat()
    
    return None

