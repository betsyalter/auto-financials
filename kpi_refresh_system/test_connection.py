import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get token
token = os.getenv('CANALYST_API_TOKEN')
print(f"Token loaded: {len(token)} characters")

# Test URL
url = "https://mds.canalyst.com/api/companies/"

# Test request
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

params = {
    'page_size': 1
}

print(f"\nTesting connection to: {url}")
print("Headers:", {k: v[:50] + '...' if k == 'Authorization' else v for k, v in headers.items()})

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS! API connection working.")
        data = response.json()
        print(f"Response has {len(data.get('results', []))} companies")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"\n❌ Exception: {type(e).__name__}: {e}")