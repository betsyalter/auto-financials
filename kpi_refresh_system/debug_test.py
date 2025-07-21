import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.canalyst_client import CanalystClient
import pandas as pd

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
print(f"Model version: {model_version}")

# Get Apple's KPIs
apple_kpis = kpi_mappings[kpi_mappings['company_id'] == company_id]
print(f"\nKPI Mappings for Apple:")
print(apple_kpis[['time_series_name', 'kpi_label', 'units']])

# Get historical data for revenue
for _, kpi in apple_kpis.iterrows():
    if 'revenue' in kpi['time_series_name'].lower():
        print(f"\nFetching data for: {kpi['time_series_name']}")
        hist = client.get_historical_data_points(
            company_id,
            model_version,
            kpi['time_series_name']
        )
        
        if hist:
            # Check first few data points
            print(f"\nFirst 3 data points:")
            for i, dp in enumerate(hist[:3]):
                print(f"\nData point {i+1}:")
                print(f"  Period: {dp['period']['name']}")
                print(f"  Value: {dp['value']}")
                print(f"  API Units: {dp['time_series']['unit']['description']}")
                print(f"  Mapped Units: {kpi['units']}")
                
                # Check value magnitude
                if dp['value']:
                    val = float(dp['value'])
                    num_digits = len(str(int(val)))
                    print(f"  Number of digits: {num_digits}")
                    if num_digits > 6:
                        print(f"  Value / 1000: {val / 1000:,.0f}")
                        print(f"  Value / 1000000: {val / 1000000:,.0f}")