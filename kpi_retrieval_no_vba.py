"""
KPI Data Retrieval System - No VBA Required
This Python script handles all KPI data retrieval and CSV generation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import time
from typing import List, Dict, Any
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kpi_retrieval.log'),
        logging.StreamHandler()
    ]
)

class KPIRetrieval:
    def __init__(self, config_path: str = None):
        """Initialize KPI Retrieval System"""
        self.config = self.load_config(config_path)
        self.export_path = Path(self.config.get('export_path', './exports'))
        self.export_path.mkdir(exist_ok=True)
        
    def load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'batch_size': 20,
            'api_timeout': 30,
            'export_path': './exports',
            'refresh_hour': 6,
            'max_retries': 3,
            'rate_limit_delay': 1,
            'max_calls_per_minute': 60
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                
        return default_config
    
    def generate_sample_data(self, ticker: str, kpi: str, periods: List[str]) -> List[float]:
        """
        Generate sample data for testing
        In production, this would call the Tegus API
        """
        # Simulate API call delay
        time.sleep(self.config['rate_limit_delay'])
        
        # Generate realistic-looking financial data
        base_value = np.random.uniform(100, 1000)
        growth_rate = np.random.uniform(0.05, 0.15)
        volatility = np.random.uniform(0.02, 0.08)
        
        values = []
        for i, period in enumerate(periods):
            if period.startswith('FY'):
                # Annual data - steady growth
                value = base_value * (1 + growth_rate) ** i
            else:
                # Quarterly data - more volatility
                quarter_growth = growth_rate / 4
                noise = np.random.normal(0, volatility)
                value = base_value * (1 + quarter_growth + noise) ** i
            
            values.append(round(value, 2))
            
        return values
    
    def get_periods(self) -> Dict[str, List[str]]:
        """Generate period arrays for annual and quarterly data"""
        current_year = datetime.now().year
        
        # Annual periods (FY24 to FY20)
        annual_periods = [f"FY{year % 100}" for year in range(current_year, current_year - 5, -1)]
        
        # Quarterly periods (Q1-25 to Q2-22)
        quarterly_periods = []
        for year in range(current_year + 1, current_year - 3, -1):
            for quarter in range(4, 0, -1):
                quarterly_periods.append(f"Q{quarter}-{year % 100}")
                if len(quarterly_periods) >= 12:
                    break
            if len(quarterly_periods) >= 12:
                break
        
        return {
            'annual': annual_periods,
            'quarterly': quarterly_periods[:12]
        }
    
    def calculate_growth_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate QoQ and YoY growth rates"""
        # Sort by date to ensure proper calculation
        df = df.sort_values(['Ticker', 'KPI_Code', 'Period'])
        
        # Calculate QoQ for quarterly data
        quarterly_mask = df['Period'].str.startswith('Q')
        df.loc[quarterly_mask, 'QoQ_Growth'] = (
            df[quarterly_mask].groupby(['Ticker', 'KPI_Code'])['Value']
            .pct_change()
            .round(4)
        )
        
        # Calculate YoY (4 periods back for quarterly, 1 for annual)
        df['YoY_Growth'] = None
        
        # Annual YoY
        annual_mask = df['Period'].str.startswith('FY')
        df.loc[annual_mask, 'YoY_Growth'] = (
            df[annual_mask].groupby(['Ticker', 'KPI_Code'])['Value']
            .pct_change(1)
            .round(4)
        )
        
        # Quarterly YoY (compare to same quarter previous year)
        if quarterly_mask.any():
            df.loc[quarterly_mask, 'YoY_Growth'] = (
                df[quarterly_mask].groupby(['Ticker', 'KPI_Code'])['Value']
                .pct_change(4)
                .round(4)
            )
        
        return df
    
    def retrieve_ticker_data(self, ticker: str, kpis: List[Dict]) -> pd.DataFrame:
        """Retrieve all KPI data for a single ticker"""
        logging.info(f"Processing ticker: {ticker}")
        
        periods = self.get_periods()
        all_periods = periods['annual'] + periods['quarterly']
        
        data = []
        for kpi in kpis:
            # In production, this would call TEGUS.CD
            values = self.generate_sample_data(ticker, kpi['code'], all_periods)
            
            for period, value in zip(all_periods, values):
                data.append({
                    'Ticker': ticker,
                    'KPI_Code': kpi['code'],
                    'KPI_Label': kpi['label'],
                    'Units': kpi['units'],
                    'Category': kpi['category'],
                    'Period': period,
                    'Value': value,
                    'Period_Type': 'Annual' if period.startswith('FY') else 'Quarterly'
                })
        
        df = pd.DataFrame(data)
        df['Retrieved_At'] = datetime.now()
        
        return df
    
    def process_all_tickers(self, tickers: List[str], kpis: List[Dict]) -> pd.DataFrame:
        """Process all tickers with rate limiting"""
        all_data = []
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            logging.info(f"Processing {i+1}/{total}: {ticker}")
            
            try:
                ticker_data = self.retrieve_ticker_data(ticker, kpis)
                all_data.append(ticker_data)
                
                # Rate limiting
                if (i + 1) % self.config['batch_size'] == 0:
                    logging.info(f"Batch complete. Pausing for rate limit...")
                    time.sleep(5)
                    
            except Exception as e:
                logging.error(f"Error processing {ticker}: {str(e)}")
                continue
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = self.calculate_growth_metrics(combined_df)
            return combined_df
        else:
            return pd.DataFrame()
    
    def export_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """Export data to CSV with metadata"""
        if filename is None:
            filename = f"kpi_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.export_path / filename
        
        # Export to CSV
        df.to_csv(filepath, index=False, encoding='utf-8')
        logging.info(f"Data exported to: {filepath}")
        
        # Create manifest
        manifest = {
            'filename': filename,
            'created_at': datetime.now().isoformat(),
            'row_count': len(df),
            'tickers': df['Ticker'].unique().tolist(),
            'kpis': df['KPI_Code'].unique().tolist(),
            'periods': {
                'annual': df[df['Period_Type'] == 'Annual']['Period'].unique().tolist(),
                'quarterly': df[df['Period_Type'] == 'Quarterly']['Period'].unique().tolist()
            }
        }
        
        manifest_path = self.export_path / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return str(filepath)
    
    def create_summary_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create a summary report of the data"""
        summary = df.groupby(['Ticker', 'KPI_Code', 'KPI_Label']).agg({
            'Value': ['min', 'max', 'mean', 'std'],
            'YoY_Growth': 'mean'
        }).round(2)
        
        summary.columns = ['Min', 'Max', 'Average', 'StdDev', 'Avg_YoY_Growth']
        return summary


def main():
    """Main execution function"""
    # Configuration
    config = {
        'tickers': ['AAPL_US', 'MSFT_US', 'AMZN_US', 'META_US'],
        'kpis': [
            {'code': 'MO_RIS_REV', 'label': 'Revenue', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_GROSS_PROFIT', 'label': 'Gross Profit', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_OP_INC', 'label': 'Operating Income', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_NET_INC', 'label': 'Net Income', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_EPS', 'label': 'EPS', 'units': 'Per Share', 'category': 'Income Statement'}
        ]
    }
    
    # Initialize retrieval system
    retriever = KPIRetrieval()
    
    # Process all tickers
    logging.info("Starting KPI data retrieval...")
    df = retriever.process_all_tickers(config['tickers'], config['kpis'])
    
    if not df.empty:
        # Export to CSV
        csv_file = retriever.export_to_csv(df)
        
        # Create summary
        summary = retriever.create_summary_report(df)
        summary_file = retriever.export_path / 'summary_report.csv'
        summary.to_csv(summary_file)
        
        logging.info(f"Process complete! Files saved to: {retriever.export_path}")
        
        # Display sample data
        print("\nSample of retrieved data:")
        print(df.head(10))
        
        print("\nSummary statistics:")
        print(summary.head())
    else:
        logging.error("No data retrieved")


if __name__ == "__main__":
    main()