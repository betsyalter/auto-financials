import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.canalyst_client import CanalystClient
import pandas as pd
import json

# Load config and create client
config = load_config('config/config.yaml')
client = CanalystClient(config)

# Load mappings
company_mappings = pd.read_csv('config/company_mappings.csv')
kpi_mappings = pd.read_csv('config/kpi_mappings.csv')

# Get Apple's data
apple = company_mappings[company_mappings['search_ticker'] == 'AAPL'].iloc[0]
company_id = apple['company_id']

print(f"Testing Apple (Company ID: {company_id})")

# Get latest model
model = client.get_latest_equity_model(company_id)
model_version = model['model_version']['name']

# Get Apple's KPIs
apple_kpis = kpi_mappings[kpi_mappings['company_id'] == company_id]

# Get raw historical data
for _, kpi in apple_kpis.iterrows():
    print(f"\nFetching RAW data for: {kpi['time_series_name']}")
    hist = client.get_historical_data_points(
        company_id,
        model_version,
        kpi['time_series_name']
    )
    
    if hist:
        print(f"\nFirst data point RAW JSON:")
        print(json.dumps(hist[0], indent=2))
        
        print(f"\nValues from first 5 periods:")
        for dp in hist[:5]:
            print(f"  {dp['period']['name']}: {dp['value']}")