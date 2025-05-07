import os
from pathlib import Path
from datetime import datetime

# Ensure the logs directory exists
log_dir = Path(__file__).resolve().parent.parent / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

# Create a log file with a timestamp
log_filename = log_dir / f'debug_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(log_filename),  # Convert Path to str
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
    },
}
