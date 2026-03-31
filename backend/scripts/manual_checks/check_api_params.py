
import requests
import sys

# Try localhost first
base_urls = [
    "http://127.0.0.1:8000/api",
    "http://localhost:8000/api",
]

asset_id = 101173
path = f"/all-assets/{asset_id}/prices/"
params = {
    "days": 365,
    "format": "list"
}

for base_url in base_urls:
    url = f"{base_url}{path}"
    print(f"Testing URL: {url} with params {params}")
    try:
        response = requests.get(url, params=params)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Response preview:", response.text[:200])
            sys.exit(0)
        elif response.status_code == 401:
             print("Status 401: Auth required, but endpoint EXISTS.")
             sys.exit(0)
        else:
            print("Response:", response.text[:200])
    except Exception as e:
        print(f"Failed to connect: {e}")

print("All attempts failed.")
