import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.canalyst_client import CanalystClient
from src.config import load_config

# Test the fixed client
config = load_config('config/config.yaml')
client = CanalystClient(config)

print("Testing fixed CanalystClient with Apple...")

try:
    company_id = "Y8S4N8"  # Apple
    
    print(f"1. Getting latest equity model for company_id: {company_id}")
    model = client.get_latest_equity_model(company_id)
    
    print(f"SUCCESS! Model version: {model['model_version']['name']}")
    
    print(f"2. Testing time series listing...")
    time_series = client.list_time_series(company_id, model['model_version']['name'], is_kpi=True)
    
    print(f"SUCCESS! Found {len(time_series)} KPI time series")
    
    # Show first few
    for ts in time_series[:3]:
        print(f"  - {ts['names'][0]}: {ts['description']}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()