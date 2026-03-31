import os
import sys
from decouple import config

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

print("--- ENV DEBUG START ---")
print(f"os.environ['DEBUG']: {os.environ.get('DEBUG')}")
try:
    print(f"decouple config('DEBUG'): {config('DEBUG')}")
except Exception as e:
    print(f"decouple config('DEBUG') ERROR: {e}")
print("--- ENV DEBUG END ---")
