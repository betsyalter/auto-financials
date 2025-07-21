import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get token
token = os.getenv('CANALYST_API_TOKEN')
print(f"Token loaded: {len(token)} characters")

# Test specific CSIN from company_mappings.csv
csin = "Y8S4N80124"  # Apple Inc
url = f"https://mds.canalyst.com/api/equity-model-series/{csin}/equity-models/"

# Test request
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

print(f"\nTesting equity model endpoint: {url}")

try:
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("SUCCESS! Equity models found")
        data = response.json()
        print(f"Found {len(data.get('results', []))} equity models")
        if data.get('results'):
            print(f"Latest model: {data['results'][0].get('model_version', {}).get('name', 'N/A')}")
    else:
        print(f"ERROR: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Also test the /latest endpoint that was failing
print(f"\nTesting /latest endpoint...")
latest_url = f"https://mds.canalyst.com/api/equity-model-series/{csin}/equity-models/latest/"

try:
    response = requests.get(latest_url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("SUCCESS! Latest model found")
        data = response.json()
        print(f"Model version: {data.get('model_version', {}).get('name', 'N/A')}")
    else:
        print(f"ERROR: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")