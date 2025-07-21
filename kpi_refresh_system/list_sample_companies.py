from src.canalyst_client import CanalystClient
from src.config import load_config

# Load config and create client
config = load_config()
client = CanalystClient(config)

# Get first 10 companies
response = client._make_request('/companies/', {'page_size': 10})

print("Sample companies in Canalyst database:\n")
for company in response.get('results', []):
    tickers = company.get('tickers', {})
    canalyst_ticker = tickers.get('Canalyst', 'N/A')
    print(f"Name: {company['name']}")
    print(f"  Canalyst Ticker: {canalyst_ticker}")
    print(f"  Company ID: {company['company_id']}")
    print(f"  Country: {company.get('country_code', 'N/A')}")
    print(f"  In Coverage: {company.get('is_in_coverage', False)}")
    print()