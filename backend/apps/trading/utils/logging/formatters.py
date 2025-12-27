"""
Custom logging formatters for the trading application.

Provides:
- ColoredFormatter: Colored console output
- JSONFormatter: Structured JSON logs
- DetailedFormatter: Verbose format with context
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class ColoredFormatter(logging.Formatter):
    """
    Formatter with ANSI colors for console output.
    
    Colors:
    - DEBUG: Cyan
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Magenta (bold)
    
    Usage in settings:
        'formatters': {
            'colored': {
                '()': 'apps.trading.utils.logging.ColoredFormatter',
                'format': '{levelname} {asctime} {name} {message}',
                'style': '{',
            },
        }
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35;1m', # Magenta bold
    }
    RESET = '\033[0m'
    
    # Emojis for each level (optional)
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }
    
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = '{',
        use_emoji: bool = True
    ):
        """
        Initialize the formatter.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            style: Format style ('{', '%', or '$')
            use_emoji: Whether to include emojis
        """
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.use_emoji = use_emoji
        
        # Check if stdout supports colors
        self._supports_colors = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        # Save original levelname
        original_levelname = record.levelname
        
        if self._supports_colors:
            # Add color
            color = self.COLORS.get(record.levelname, '')
            emoji = self.EMOJIS.get(record.levelname, '') if self.use_emoji else ''
            
            if emoji:
                record.levelname = f"{emoji} {color}{record.levelname}{self.RESET}"
            else:
                record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # Format the message
        result = super().format(record)
        
        # Restore original levelname
        record.levelname = original_levelname
        
        return result


class JSONFormatter(logging.Formatter):
    """
    Formatter for structured JSON logs.
    
    Outputs each log entry as a single JSON line, suitable for
    log aggregation systems like Elasticsearch, Splunk, etc.
    
    Usage in settings:
        'formatters': {
            'json': {
                '()': 'apps.trading.utils.logging.JSONFormatter',
            },
        }
    """
    
    # Fields to include in the output
    STANDARD_FIELDS = [
        'timestamp',
        'level',
        'logger',
        'message',
        'module',
        'function',
        'line',
    ]
    
    # Extra fields to look for in the record
    EXTRA_FIELDS = [
        'user_id',
        'broker_type',
        'broker_id',
        'sync_type',
        'asset_id',
        'symbol',
        'request_id',
        'ip_address',
        'path',
        'method',
        'status_code',
        'duration',
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields if present
        for field in self.EXTRA_FIELDS:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        # Add custom 'extra' dict if present
        if hasattr(record, 'details') and isinstance(record.details, dict):
            log_data['details'] = record.details
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info),
            }
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class DetailedFormatter(logging.Formatter):
    """
    Detailed formatter with context information.
    
    Format:
    [LEVEL] YYYY-MM-DD HH:MM:SS | module.function:line | message | {context}
    
    Usage in settings:
        'formatters': {
            'detailed': {
                '()': 'apps.trading.utils.logging.DetailedFormatter',
            },
        }
    """
    
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: str = '%Y-%m-%d %H:%M:%S',
        style: str = '%'
    ):
        """Initialize the formatter."""
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with details."""
        # Build the main message
        timestamp = datetime.fromtimestamp(record.created).strftime(self.datefmt)
        location = f"{record.module}.{record.funcName}:{record.lineno}"
        
        parts = [
            f"[{record.levelname:8}]",
            timestamp,
            "|",
            f"{location:40}",
            "|",
            record.getMessage(),
        ]
        
        # Add context if present
        context_items = []
        for field in ['user_id', 'broker_type', 'sync_type', 'symbol']:
            if hasattr(record, field):
                context_items.append(f"{field}={getattr(record, field)}")
        
        if context_items:
            parts.append("|")
            parts.append("{" + ", ".join(context_items) + "}")
        
        result = " ".join(parts)
        
        # Add exception if present
        if record.exc_info:
            result += "\n" + self.formatException(record.exc_info)
        
        return result


class TradingLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds trading context to all log messages.
    
    Usage:
        logger = logging.getLogger('trading')
        logger = TradingLoggerAdapter(logger, {'user_id': 1, 'broker': 'saxo'})
        logger.info("Message")  # Will include user_id and broker
    """
    
    def process(self, msg: str, kwargs: Dict) -> tuple:
        """Process the log message and add context."""
        # Get or create extra dict
        extra = kwargs.get('extra', {})
        
        # Add adapter context
        extra.update(self.extra)
        
        kwargs['extra'] = extra
        return msg, kwargs


def get_trading_logger(
    name: str,
    user_id: Optional[int] = None,
    broker_type: Optional[str] = None,
    **extra
) -> TradingLoggerAdapter:
    """
    Get a logger with trading context.
    
    Args:
        name: Logger name (e.g., 'trading.brokers.saxo')
        user_id: User ID to include in all log messages
        broker_type: Broker type to include
        **extra: Additional context to include
        
    Returns:
        TradingLoggerAdapter with context
    
    Usage:
        logger = get_trading_logger('trading.sync', user_id=1, broker_type='saxo')
        logger.info("Starting sync")  # Includes user_id and broker_type
    """
    base_logger = logging.getLogger(name)
    
    context = extra.copy()
    if user_id:
        context['user_id'] = user_id
    if broker_type:
        context['broker_type'] = broker_type
    
    return TradingLoggerAdapter(base_logger, context)

