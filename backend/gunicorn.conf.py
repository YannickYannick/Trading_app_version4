# Nom du processus
proc_name = 'trading_app_v4'

# Adresses d'écoute
bind = '0.0.0.0:8000'

# Workers — fixed at 2 for Railway Hobby plan (0.5 vCPU, 0.5 GB RAM)
workers = 2
worker_class = 'sync'
timeout = 120  # Augmenté pour les requêtes longues (backtests, etc.)
keepalive = 5

# Periodic worker restarts to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging — access log disabled to reduce memory overhead; warnings only
accesslog = None
errorlog = 'logs/error.log'
loglevel = 'warning'

# Daemon
daemon = False
