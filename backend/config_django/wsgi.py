"""
WSGI config for trading_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""
import os
import traceback

print("[WSGI] wsgi.py imported — starting WSGI setup", flush=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.production')

try:
    from django.core.wsgi import get_wsgi_application

    print("[WSGI] Calling get_wsgi_application()...", flush=True)
    application = get_wsgi_application()
    print("[WSGI] get_wsgi_application() succeeded — WSGI application is ready", flush=True)

except Exception as e:
    print(f"[WSGI] FATAL: get_wsgi_application() raised an exception: {e}", flush=True)
    print("[WSGI] Full traceback:", flush=True)
    traceback.print_exc()
    raise

