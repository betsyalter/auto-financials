import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

token = os.getenv('CANALYST_API_TOKEN')
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

print("=== Debugging Apple Equity Model Access ===\n")

# 1. Let's get more detailed info about Apple
print("1. Getting detailed Apple company info...")
url = "https://mds.canalyst.com/api/companies/"
params = {
    'ticker_canalyst': 'AAPL_US',
    'page_size': 1
}

response = requests.get(url, headers=headers, params=params, timeout=30)
if response.status_code == 200:
    company_data = response.json()['results'][0]
    print(f"Full company data:")
    print(json.dumps(company_data, indent=2))
    
    company_id = company_data['company_id']
    print(f"\nCompany ID: {company_id}")
    
    # 2. Let's try different variations of the equity model endpoint
    print(f"\n2. Testing different equity model endpoints...")
    
    test_urls = [
        f"https://mds.canalyst.com/api/equity-model-series/{company_id}/",
        f"https://mds.canalyst.com/api/equity-model-series/{company_id}/equity-models/",
        f"https://mds.canalyst.com/api/companies/{company_id}/equity-models/",
        f"https://mds.canalyst.com/api/companies/{company_id}/equity-model-series/",
        f"https://mds.canalyst.com/api/equity-models/?company_id={company_id}",
    ]
    
    for test_url in test_urls:
        print(f"\nTesting: {test_url}")
        try:
            resp = requests.get(test_url, headers=headers, timeout=30)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  SUCCESS! Keys: {list(data.keys())}")
                if 'results' in data:
                    print(f"  Results count: {len(data['results'])}")
        except Exception as e:
            print(f"  Error: {e}")

# 3. Let's also search for any equity model series in general
print(f"\n3. Searching for ANY equity model series...")
try:
    resp = requests.get("https://mds.canalyst.com/api/equity-model-series/", headers=headers, params={'page_size': 5}, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {len(data.get('results', []))} equity model series examples:")
        for series in data.get('results', [])[:3]:
            print(f"  - Company: {series.get('company', {}).get('name')}")
            print(f"    Series ID: {series.get('id')}")
            print(f"    Company ID: {series.get('company', {}).get('company_id')}")
    else:
        print(f"Error getting equity model series list: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")