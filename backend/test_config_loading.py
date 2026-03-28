from decouple import config
import os

print(f"CWD: {os.getcwd()}")
print(f"File exists .env: {os.path.exists('.env')}")
try:
    print(f"DB_HOST: {config('DB_HOST')}")
except Exception as e:
    print(f"Error loading DB_HOST: {e}")

print(f"DEBUG: {config('DEBUG', default='NOT_FOUND')}")
