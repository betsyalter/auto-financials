import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.canalyst_client import CanalystClient
from src.config import load_config

# Test getting ALL time series vs just KPIs
config = load_config('config/config.yaml')
client = CanalystClient(config)

company_id = "Y8S4N8"  # Apple

print("Testing the exact change we want to make...")

# Get latest model
model = client.get_latest_equity_model(company_id)
model_version = model['model_version']['name']

print(f"\nTesting with is_kpi=True (current behavior):")
kpis_only = client.list_time_series(company_id, model_version, is_kpi=True)
print(f"Result: {len(kpis_only)} items")

print(f"\nTesting with is_kpi=None (proposed change):")
all_series = client.list_time_series(company_id, model_version, is_kpi=None)
print(f"Result: {len(all_series)} items")

print(f"\nTesting with is_kpi=False:")
non_kpis = client.list_time_series(company_id, model_version, is_kpi=False)
print(f"Result: {len(non_kpis)} items")

print("\nVerifying the data structure is the same:")
if kpis_only:
    print("Sample KPI structure:", list(kpis_only[0].keys())[:5])
if all_series:
    print("Sample ALL structure:", list(all_series[0].keys())[:5])
    
print("\nChecking if important metrics are included:")
important_metrics = ['revenue', 'ebitda', 'income', 'margin', 'cash']
for metric in important_metrics:
    count = len([ts for ts in all_series if metric.lower() in ts['description'].lower()])
    print(f"  '{metric}' metrics: {count}")