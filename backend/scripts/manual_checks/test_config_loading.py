from decouple import config
import os
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

print(f"CWD: {os.getcwd()}")
print(f"File exists .env: {os.path.exists('.env')}")
try:
    print(f"DB_HOST: {config('DB_HOST')}")
except Exception as e:
    print(f"Error loading DB_HOST: {e}")

print(f"DEBUG: {config('DEBUG', default='NOT_FOUND')}")
