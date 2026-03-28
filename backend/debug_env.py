import os
from decouple import config

print("--- ENV DEBUG START ---")
print(f"os.environ['DEBUG']: {os.environ.get('DEBUG')}")
try:
    print(f"decouple config('DEBUG'): {config('DEBUG')}")
except Exception as e:
    print(f"decouple config('DEBUG') ERROR: {e}")
print("--- ENV DEBUG END ---")
