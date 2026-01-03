import multiprocessing

# Nom du processus
proc_name = 'trading_app_v4'

# Adresses d'écoute
bind = '127.0.0.1:8000'

# Workers
# (2 x CPUs) + 1 est la formule recommandée
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
timeout = 120  # Augmenté pour les requêtes longues (backtests, etc.)
keepalive = 5

# Logging
accesslog = 'logs/access.log'
errorlog = 'logs/error.log'
loglevel = 'info'

# Daemon
daemon = False
