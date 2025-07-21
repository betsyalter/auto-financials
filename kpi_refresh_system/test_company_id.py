import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get token
token = os.getenv('CANALYST_API_TOKEN')

# Test with company_id instead of csin
company_id = "Y8S4N8"  # Apple Inc (short form)
csin = "Y8S4N80124"    # Apple Inc (long form)

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

print(f"Testing with company_id: {company_id}")
url1 = f"https://mds.canalyst.com/api/equity-model-series/{company_id}/equity-models/"

try:
    response = requests.get(url1, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("SUCCESS with company_id!")
        data = response.json()
        print(f"Found {len(data.get('results', []))} equity models")
    else:
        print(f"ERROR with company_id: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
except Exception as e:
    print(f"Exception: {e}")

# Let's also check if we can find this company in the companies endpoint
print(f"\nSearching for Apple in companies endpoint...")
url2 = "https://mds.canalyst.com/api/companies/"
params = {
    'ticker_canalyst': 'AAPL_US',
    'page_size': 5
}

try:
    response = requests.get(url2, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        print(f"Found {len(results)} companies")
        for company in results:
            print(f"Company: {company.get('name')}")
            print(f"  Company ID: {company.get('company_id')}")
            print(f"  Tickers: {company.get('tickers', {})}")
            print(f"  Is in coverage: {company.get('is_in_coverage', False)}")
            print()
        
except Exception as e:
    print(f"Exception: {e}")