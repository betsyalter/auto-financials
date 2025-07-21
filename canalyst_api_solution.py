"""
Canalyst REST API Solution for KPI Retrieval
Uses direct API calls to retrieve financial data
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('canalyst_api.log'),
        logging.StreamHandler()
    ]
)

class CanalystAPI:
    def __init__(self, api_key: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Canalyst API client
        
        Args:
            api_key: API key (if using token auth)
            username: Username (if using basic auth)
            password: Password (if using basic auth)
        """
        self.base_url = "https://mds.canalyst.com/api"
        self.session = requests.Session()
        
        # Set up authentication
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            })
        elif username and password:
            self.session.auth = (username, password)
            self.session.headers.update({'Content-Type': 'application/json'})
        else:
            # Try to get credentials from environment variables
            api_key = os.getenv('CANALYST_API_KEY')
            username = os.getenv('CANALYST_USERNAME')
            password = os.getenv('CANALYST_PASSWORD')
            
            if api_key:
                self.session.headers.update({
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                })
            elif username and password:
                self.session.auth = (username, password)
                self.session.headers.update({'Content-Type': 'application/json'})
            else:
                logging.warning("No authentication credentials provided")
        
        self.output_dir = Path('./canalyst_exports')
        self.output_dir.mkdir(exist_ok=True)
        
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                logging.info("API connection successful")
                print("✅ Connected to Canalyst API")
                return True
            else:
                logging.error(f"API connection failed: {response.status_code}")
                print(f"❌ API connection failed: {response.status_code}")
                
                if response.status_code == 401:
                    print("\n⚠️  Authentication required. Please provide:")
                    print("1. API key via CANALYST_API_KEY environment variable, or")
                    print("2. Username/password via CANALYST_USERNAME and CANALYST_PASSWORD")
                
                return False
                
        except Exception as e:
            logging.error(f"Connection error: {str(e)}")
            print(f"❌ Connection error: {str(e)}")
            return False
    
    def search_company(self, ticker: str) -> Optional[Dict]:
        """Search for a company by ticker"""
        try:
            # Try companies endpoint
            response = self.session.get(
                f"{self.base_url}/companies/",
                params={'search': ticker, 'ticker': ticker}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle paginated results
                if 'results' in data:
                    companies = data['results']
                else:
                    companies = data if isinstance(data, list) else [data]
                
                # Find exact ticker match
                for company in companies:
                    if company.get('ticker', '').upper() == ticker.upper().replace(' ', '_'):
                        logging.info(f"Found company: {company.get('name')} ({ticker})")
                        return company
                
                # If no exact match, return first result
                if companies:
                    logging.info(f"Using closest match for {ticker}: {companies[0].get('name')}")
                    return companies[0]
            
            logging.warning(f"Company not found: {ticker}")
            return None
            
        except Exception as e:
            logging.error(f"Error searching company {ticker}: {str(e)}")
            return None
    
    def get_model_series(self, company_id: str) -> Optional[List[Dict]]:
        """Get available model series for a company"""
        try:
            response = self.session.get(
                f"{self.base_url}/equity-model-series/",
                params={'company': company_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'results' in data:
                    return data['results']
                else:
                    return data if isinstance(data, list) else [data]
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting model series: {str(e)}")
            return None
    
    def get_time_series_data(self, series_url: str) -> pd.DataFrame:
        """Get time series data from a model series"""
        try:
            response = self.session.get(series_url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract time series data
                if 'time_series' in data:
                    ts_data = data['time_series']
                elif 'data' in data:
                    ts_data = data['data']
                else:
                    ts_data = data
                
                # Convert to DataFrame
                if isinstance(ts_data, dict):
                    df = pd.DataFrame.from_dict(ts_data, orient='index')
                    df.index = pd.to_datetime(df.index)
                    return df
                elif isinstance(ts_data, list):
                    return pd.DataFrame(ts_data)
                
            return pd.DataFrame()
            
        except Exception as e:
            logging.error(f"Error getting time series: {str(e)}")
            return pd.DataFrame()
    
    def extract_kpis_for_ticker(self, ticker: str) -> pd.DataFrame:
        """Extract all KPIs for a given ticker"""
        logging.info(f"Processing {ticker}...")
        
        # Search for company
        company = self.search_company(ticker)
        if not company:
            logging.warning(f"Company not found: {ticker}")
            return pd.DataFrame()
        
        company_id = company.get('id') or company.get('company_id')
        company_name = company.get('name', ticker)
        
        # Get model series
        model_series = self.get_model_series(company_id)
        if not model_series:
            logging.warning(f"No model series found for {company_name}")
            return pd.DataFrame()
        
        all_kpi_data = []
        
        # Define KPI mappings
        kpi_keywords = {
            'revenue': ['revenue', 'sales', 'turnover'],
            'gross_profit': ['gross_profit', 'gross_income'],
            'operating_income': ['operating_income', 'operating_profit', 'ebit'],
            'net_income': ['net_income', 'net_profit', 'earnings'],
            'eps': ['eps', 'earnings_per_share'],
            'free_cash_flow': ['free_cash_flow', 'fcf'],
            'total_assets': ['total_assets', 'assets'],
            'total_debt': ['total_debt', 'debt']
        }
        
        # Process each model series
        for series in model_series:
            series_name = series.get('name', '').lower()
            series_url = series.get('url') or series.get('detail_url')
            
            if not series_url:
                continue
            
            # Check if this series contains KPIs we want
            for kpi_name, keywords in kpi_keywords.items():
                if any(keyword in series_name for keyword in keywords):
                    # Get time series data
                    df = self.get_time_series_data(series_url)
                    
                    if not df.empty:
                        # Process each column (might have multiple related metrics)
                        for col in df.columns:
                            # Create records for each time period
                            for idx, value in df[col].items():
                                if pd.notna(value):
                                    all_kpi_data.append({
                                        'Ticker': ticker,
                                        'Company': company_name,
                                        'KPI_Category': kpi_name,
                                        'KPI_Label': self.format_kpi_label(col),
                                        'Period_Date': idx,
                                        'Period': self.format_period(idx),
                                        'Value': float(value),
                                        'Units': self.infer_units(kpi_name),
                                        'Retrieved_At': datetime.now()
                                    })
        
        # Rate limiting
        time.sleep(0.5)
        
        return pd.DataFrame(all_kpi_data)
    
    def format_kpi_label(self, raw_label: str) -> str:
        """Format KPI label to be human-readable"""
        # Remove underscores and capitalize
        label = raw_label.replace('_', ' ').title()
        
        # Common replacements
        replacements = {
            'Eps': 'EPS',
            'Fcf': 'FCF',
            'Ebit': 'EBIT',
            'Ebitda': 'EBITDA'
        }
        
        for old, new in replacements.items():
            label = label.replace(old, new)
        
        return label
    
    def format_period(self, date) -> str:
        """Format date to period string"""
        if pd.isna(date):
            return "Unknown"
        
        if not isinstance(date, pd.Timestamp):
            date = pd.to_datetime(date)
        
        # Check if it's a quarter end
        if date.month in [3, 6, 9, 12]:
            quarter = (date.month - 1) // 3 + 1
            return f"Q{quarter}-{date.year % 100}"
        else:
            # Default to fiscal year
            return f"FY{date.year % 100}"
    
    def infer_units(self, kpi_name: str) -> str:
        """Infer units based on KPI name"""
        if 'eps' in kpi_name.lower():
            return 'Per Share'
        elif any(term in kpi_name.lower() for term in ['revenue', 'profit', 'income', 'cash', 'assets', 'debt']):
            return 'Millions'
        else:
            return 'Units'
    
    def process_multiple_tickers(self, tickers: List[str]) -> pd.DataFrame:
        """Process multiple tickers"""
        all_data = []
        total = len(tickers)
        
        print(f"\n📊 Processing {total} tickers...")
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{total}] {ticker}")
            
            ticker_data = self.extract_kpis_for_ticker(ticker)
            
            if not ticker_data.empty:
                all_data.append(ticker_data)
                print(f"  ✅ Retrieved {len(ticker_data)} data points")
            else:
                print(f"  ⚠️  No data found")
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            return self.calculate_growth_metrics(combined_df)
        
        return pd.DataFrame()
    
    def calculate_growth_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate growth metrics"""
        if df.empty:
            return df
        
        # Sort by date
        df = df.sort_values(['Ticker', 'KPI_Label', 'Period_Date'])
        
        # Calculate growth
        for ticker in df['Ticker'].unique():
            for kpi in df['KPI_Label'].unique():
                mask = (df['Ticker'] == ticker) & (df['KPI_Label'] == kpi)
                
                if mask.any():
                    # Period-over-period growth
                    df.loc[mask, 'PoP_Growth'] = df.loc[mask, 'Value'].pct_change()
                    
                    # Year-over-year growth
                    if 'Q' in df.loc[mask, 'Period'].iloc[0]:
                        # Quarterly: 4 periods back
                        df.loc[mask, 'YoY_Growth'] = df.loc[mask, 'Value'].pct_change(4)
                    else:
                        # Annual: 1 period back
                        df.loc[mask, 'YoY_Growth'] = df.loc[mask, 'Value'].pct_change(1)
        
        return df
    
    def export_data(self, df: pd.DataFrame) -> Optional[Path]:
        """Export data to CSV"""
        if df.empty:
            logging.warning("No data to export")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Main export
        filename = f"canalyst_kpi_data_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Clean up for export
        export_df = df.drop(columns=['Period_Date'], errors='ignore')
        export_df.to_csv(filepath, index=False, encoding='utf-8')
        
        # Create pivot for easier analysis
        pivot_df = df.pivot_table(
            index=['Ticker', 'Company', 'KPI_Label', 'Units'],
            columns='Period',
            values='Value',
            aggfunc='first'
        ).reset_index()
        
        pivot_file = self.output_dir / f"canalyst_pivot_{timestamp}.csv"
        pivot_df.to_csv(pivot_file, index=False)
        
        # Create summary
        summary = df.groupby(['Ticker', 'KPI_Label']).agg({
            'Value': ['count', 'mean', 'min', 'max'],
            'YoY_Growth': lambda x: x.dropna().mean()
        }).round(2)
        
        summary_file = self.output_dir / f"canalyst_summary_{timestamp}.csv"
        summary.to_csv(summary_file)
        
        print(f"\n📁 Files exported to: {self.output_dir}")
        print(f"  - Main data: {filename}")
        print(f"  - Pivot view: {pivot_file.name}")
        print(f"  - Summary: {summary_file.name}")
        
        return filepath


def main():
    """Main execution function"""
    
    # Configuration
    TICKERS = [
        "AAPL US",
        "MSFT US",
        "AMZN US",
        "GOOGL US",
        "TSLA US"
    ]
    
    print("\n🚀 Canalyst API KPI Retrieval")
    print("=" * 50)
    
    # Check for credentials
    if not (os.getenv('CANALYST_API_KEY') or (os.getenv('CANALYST_USERNAME') and os.getenv('CANALYST_PASSWORD'))):
        print("\n⚠️  No credentials found!")
        print("\nPlease set one of the following:")
        print("1. Environment variable: CANALYST_API_KEY")
        print("2. Environment variables: CANALYST_USERNAME and CANALYST_PASSWORD")
        print("\nExample:")
        print('  set CANALYST_API_KEY=your_api_key_here')
        print('  # OR')
        print('  set CANALYST_USERNAME=your_username')
        print('  set CANALYST_PASSWORD=your_password')
        return
    
    # Initialize API client
    api = CanalystAPI()
    
    # Test connection
    if not api.test_connection():
        return
    
    print(f"\n📋 Ready to process {len(TICKERS)} tickers")
    
    if input("\nProceed? (y/n): ").lower() != 'y':
        print("Cancelled")
        return
    
    # Process tickers
    start_time = time.time()
    df = api.process_multiple_tickers(TICKERS)
    
    if df.empty:
        print("\n❌ No data retrieved")
        return
    
    # Export data
    api.export_data(df)
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n✅ Complete! Processed in {elapsed:.1f} seconds")
    print(f"\n📊 Summary:")
    print(f"  - Records: {len(df):,}")
    print(f"  - Tickers: {df['Ticker'].nunique()}")
    print(f"  - KPIs: {df['KPI_Label'].nunique()}")
    print(f"  - Date range: {df['Period'].min()} to {df['Period'].max()}")
    
    # Show sample
    print("\n📋 Sample data:")
    print(df[['Ticker', 'KPI_Label', 'Period', 'Value', 'YoY_Growth']].head(10))


if __name__ == "__main__":
    main()