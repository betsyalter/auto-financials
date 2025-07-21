import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Load the company mappings to see the actual data
company_mappings = pd.read_csv('config/company_mappings.csv')

print("Company mappings columns:", company_mappings.columns.tolist())
print("\nFirst row of company mappings:")
first_company = company_mappings.iloc[0]
print(f"  search_ticker: {first_company['search_ticker']}")
print(f"  company_id: {first_company['company_id']}")
print(f"  csin: {first_company['csin']}")
print(f"  name: {first_company['name']}")

# Load KPI mappings
kpi_mappings = pd.read_csv('config/kpi_mappings.csv')
print(f"\nKPI mappings columns: {kpi_mappings.columns.tolist()}")
print(f"First row csin: {kpi_mappings.iloc[0]['csin']}")

# Check if any KPIs match the first company
matching_kpis = kpi_mappings[kpi_mappings['csin'] == first_company['csin']]
print(f"\nKPIs matching {first_company['search_ticker']} (csin={first_company['csin']}): {len(matching_kpis)}")

# Also check if any match the company_id 
matching_kpis_by_id = kpi_mappings[kpi_mappings['csin'] == first_company['company_id']]
print(f"KPIs matching {first_company['search_ticker']} (company_id={first_company['company_id']}): {len(matching_kpis_by_id)}")

print("\nActual csin values in KPI mappings:")
print(kpi_mappings['csin'].unique())