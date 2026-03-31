
import requests
import sys

base_url = "http://127.0.0.1:8000/api"
asset_id = 101173
path = f"/all-assets/{asset_id}/prices/"
url = f"{base_url}{path}"

# Test 1: format=list (Expected: 404)
print(f"--- Test 1: {url}?format=list ---")
response = requests.get(url, params={"days": 365, "format": "list"})
print(f"Status: {response.status_code}")

# Test 2: output_format=list (Expected: 401)
print(f"--- Test 2: {url}?output_format=list ---")
response = requests.get(url, params={"days": 365, "output_format": "list"})
print(f"Status: {response.status_code}")

# Test 3: format=json (Expected: 401)
print(f"--- Test 3: {url}?format=json ---")
response = requests.get(url, params={"days": 365, "format": "json"})
print(f"Status: {response.status_code}")
