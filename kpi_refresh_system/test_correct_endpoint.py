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

print("Testing the CORRECT endpoint format for Apple...")

# Use the endpoint format suggested by equity_model_series_set
company_id = "Y8S4N8"
url = "https://mds.canalyst.com/api/equity-model-series/"
params = {'company_id': company_id}

print(f"URL: {url}")
print(f"Params: {params}")

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"SUCCESS! Found equity model series for Apple!")
        print(f"Number of series: {len(data.get('results', []))}")
        
        for series in data.get('results', [])[:2]:  # Show first 2
            print(f"\nSeries:")
            print(f"  Company: {series.get('company', {}).get('name')}")
            print(f"  Company ID: {series.get('company', {}).get('company_id')}")
            print(f"  Self URL: {series.get('self', 'N/A')}")
            
            # If we have a series, let's try to get its models
            if 'self' in series:
                series_url = series['self'] + "equity-models/"
                print(f"  Trying models at: {series_url}")
                
                model_resp = requests.get(series_url, headers=headers, timeout=30)
                print(f"  Models status: {model_resp.status_code}")
                
                if model_resp.status_code == 200:
                    model_data = model_resp.json()
                    print(f"  Found {len(model_data.get('results', []))} models")
                    
                    # Try latest model
                    latest_url = series_url + "latest/"
                    latest_resp = requests.get(latest_url, headers=headers, timeout=30)
                    print(f"  Latest model status: {latest_resp.status_code}")
                    
                    if latest_resp.status_code == 200:
                        latest_data = latest_resp.json()
                        print(f"  Latest model version: {latest_data.get('model_version', {}).get('name', 'N/A')}")
                    
    else:
        print(f"ERROR: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"Exception: {e}")