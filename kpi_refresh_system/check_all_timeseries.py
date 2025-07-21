import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.canalyst_client import CanalystClient
from src.config import load_config

# Test the fixed client
config = load_config('config/config.yaml')
client = CanalystClient(config)

print("Checking Apple time series...")

company_id = "Y8S4N8"  # Apple

# Get latest model
model = client.get_latest_equity_model(company_id)
print(f"Model version: {model['model_version']['name']}")

# Get ALL time series (not just KPIs)
print("\n1. Getting ALL time series...")
all_time_series = client.list_time_series(company_id, model['model_version']['name'], is_kpi=None)
print(f"Total time series: {len(all_time_series)}")

# Get only KPIs
print("\n2. Getting only KPIs...")
kpis_only = client.list_time_series(company_id, model['model_version']['name'], is_kpi=True)
print(f"KPIs only: {len(kpis_only)}")

# Get non-KPIs
print("\n3. Getting non-KPIs...")
non_kpis = client.list_time_series(company_id, model['model_version']['name'], is_kpi=False)
print(f"Non-KPIs: {len(non_kpis)}")

# Show some examples of non-KPIs
print("\nExamples of non-KPI time series:")
for ts in non_kpis[:10]:
    print(f"  - {ts['names'][0]}: {ts['description']} (Category: {ts['category']['description']})")

# Check if specific common metrics are available
print("\nSearching for common metrics...")
search_terms = ['revenue', 'ebitda', 'eps', 'margin', 'cash flow']
for term in search_terms:
    matches = [ts for ts in all_time_series if term.lower() in ts['description'].lower()]
    print(f"\n'{term}' matches: {len(matches)}")
    for ts in matches[:3]:
        print(f"  - {ts['names'][0]}: {ts['description']} (is_kpi: {ts.get('is_kpi', False)})")