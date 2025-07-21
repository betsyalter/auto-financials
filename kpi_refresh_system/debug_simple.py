import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.canalyst_client import CanalystClient
from src.data_processor import KPIDataProcessor
import pandas as pd

# Load everything
config = load_config('config/config.yaml')
client = CanalystClient(config)
processor = KPIDataProcessor(config)

company_mappings = pd.read_csv('config/company_mappings.csv')
kpi_mappings = pd.read_csv('config/kpi_mappings.csv')

# Get Apple data
apple = company_mappings[company_mappings['search_ticker'] == 'AAPL'].iloc[0]
company_id = apple['company_id']

model = client.get_latest_equity_model(company_id)
model_version = model['model_version']['name']

apple_kpis = kpi_mappings[kpi_mappings['company_id'] == company_id]

# Get data
historical_data = []
for _, kpi in apple_kpis.iterrows():
    hist = client.get_historical_data_points(
        company_id,
        model_version,
        kpi['time_series_name']
    )
    historical_data.extend(hist)

hist_periods_data = client.get_historical_periods(company_id, model_version)

# Process data
api_data = {
    'historical_data': historical_data,
    'forecast_data': [],
    'periods': hist_periods_data,
    'time_series_info': apple_kpis.to_dict('records')
}

df = processor.process_company_data(company_id, api_data, apple_kpis)

print("DataFrame Index:")
for idx in df.index:
    print(f"  {idx}")
    
print("\nFirst few values:")
print(df.iloc[0, :5])