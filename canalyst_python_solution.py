"""
Canalyst Python API Solution - Direct KPI Retrieval
No Excel or VBA needed!
"""

import canalyst_candas as cd
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('canalyst_retrieval.log'),
        logging.StreamHandler()
    ]
)

class CanalystKPIRetrieval:
    def __init__(self, output_dir='./exports'):
        """Initialize Canalyst KPI retrieval system"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Rate limiting settings
        self.rate_limit_delay = 1  # seconds between API calls
        self.batch_size = 20
        
        logging.info("Canalyst KPI Retrieval initialized")
    
    def test_connection(self, test_ticker="AAPL US"):
        """Test Canalyst API connection"""
        try:
            logging.info(f"Testing connection with {test_ticker}...")
            model = cd.Model(ticker=test_ticker)
            df = model.model_frame()
            
            if df.empty:
                logging.error("Connection test failed - empty dataframe")
                return False
            
            logging.info(f"Connection successful! Retrieved {len(df)} rows")
            print(f"✅ Canalyst connection working! Sample data shape: {df.shape}")
            return True
            
        except Exception as e:
            logging.error(f"Connection test failed: {str(e)}")
            print(f"❌ Connection failed: {str(e)}")
            print("\nPlease make sure:")
            print("1. canalyst_candas is installed: pip install canalyst-candas")
            print("2. You have valid Canalyst API credentials")
            print("3. Your credentials are properly configured")
            return False
    
    def get_kpi_mapping(self):
        """Define KPI mapping for Canalyst data"""
        # Map friendly names to Canalyst model fields
        return {
            'Revenue': {
                'fields': ['revenue', 'total_revenue', 'net_revenue'],
                'units': 'Millions',
                'category': 'Income Statement'
            },
            'Gross Profit': {
                'fields': ['gross_profit', 'gross_income'],
                'units': 'Millions',
                'category': 'Income Statement'
            },
            'Operating Income': {
                'fields': ['operating_income', 'operating_profit', 'ebit'],
                'units': 'Millions',
                'category': 'Income Statement'
            },
            'Net Income': {
                'fields': ['net_income', 'net_profit'],
                'units': 'Millions',
                'category': 'Income Statement'
            },
            'EPS': {
                'fields': ['eps', 'earnings_per_share', 'diluted_eps'],
                'units': 'Per Share',
                'category': 'Income Statement'
            },
            'Free Cash Flow': {
                'fields': ['free_cash_flow', 'fcf'],
                'units': 'Millions',
                'category': 'Cash Flow'
            },
            'Total Assets': {
                'fields': ['total_assets', 'assets'],
                'units': 'Millions',
                'category': 'Balance Sheet'
            },
            'Total Debt': {
                'fields': ['total_debt', 'debt'],
                'units': 'Millions',
                'category': 'Balance Sheet'
            }
        }
    
    def extract_kpi_data(self, ticker):
        """Extract KPI data for a single ticker"""
        try:
            logging.info(f"Processing {ticker}...")
            
            # Get model data
            model = cd.Model(ticker=ticker)
            df = model.model_frame()
            
            if df.empty:
                logging.warning(f"No data found for {ticker}")
                return pd.DataFrame()
            
            # Get time series data
            time_series = model.time_series
            
            # Extract KPIs
            kpi_data = []
            kpi_mapping = self.get_kpi_mapping()
            
            for kpi_name, config in kpi_mapping.items():
                # Try to find the KPI in the model
                value_found = False
                
                for field in config['fields']:
                    if hasattr(time_series, field):
                        try:
                            # Get the time series for this KPI
                            kpi_series = getattr(time_series, field)
                            
                            # Convert to dataframe
                            if hasattr(kpi_series, 'to_frame'):
                                kpi_df = kpi_series.to_frame()
                            else:
                                kpi_df = pd.DataFrame(kpi_series)
                            
                            # Process each period
                            for idx, value in kpi_df.iterrows():
                                kpi_data.append({
                                    'Ticker': ticker,
                                    'KPI_Label': kpi_name,
                                    'KPI_Code': field,
                                    'Units': config['units'],
                                    'Category': config['category'],
                                    'Period': self.format_period(idx),
                                    'Period_Date': idx,
                                    'Value': float(value.iloc[0]) if not pd.isna(value.iloc[0]) else None,
                                    'Retrieved_At': datetime.now()
                                })
                            
                            value_found = True
                            break
                            
                        except Exception as e:
                            logging.debug(f"Could not extract {field}: {str(e)}")
                            continue
                
                if not value_found:
                    logging.warning(f"Could not find {kpi_name} for {ticker}")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return pd.DataFrame(kpi_data)
            
        except Exception as e:
            logging.error(f"Error processing {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def format_period(self, date):
        """Format date to period string (FY24, Q1-24, etc.)"""
        if pd.isna(date):
            return "Unknown"
        
        # Convert to datetime if needed
        if not isinstance(date, pd.Timestamp):
            date = pd.to_datetime(date)
        
        year = date.year
        month = date.month
        
        # Determine if it's quarterly or annual
        if month in [3, 6, 9, 12]:  # Quarter ends
            quarter = (month - 1) // 3 + 1
            return f"Q{quarter}-{year % 100}"
        elif month == 12:  # Fiscal year end
            return f"FY{year % 100}"
        else:
            # Default to quarter
            quarter = (month - 1) // 3 + 1
            return f"Q{quarter}-{year % 100}"
    
    def calculate_growth_metrics(self, df):
        """Calculate QoQ and YoY growth rates"""
        if df.empty:
            return df
        
        # Sort by date
        df = df.sort_values(['Ticker', 'KPI_Label', 'Period_Date'])
        
        # Calculate growth for each ticker/KPI combination
        for ticker in df['Ticker'].unique():
            for kpi in df['KPI_Label'].unique():
                mask = (df['Ticker'] == ticker) & (df['KPI_Label'] == kpi)
                
                if mask.any():
                    # QoQ growth (1 period)
                    df.loc[mask, 'QoQ_Growth'] = df.loc[mask, 'Value'].pct_change()
                    
                    # YoY growth (4 quarters or 1 year)
                    if 'Q' in df.loc[mask, 'Period'].iloc[0]:
                        # Quarterly data - 4 periods back
                        df.loc[mask, 'YoY_Growth'] = df.loc[mask, 'Value'].pct_change(4)
                    else:
                        # Annual data - 1 period back
                        df.loc[mask, 'YoY_Growth'] = df.loc[mask, 'Value'].pct_change(1)
        
        return df
    
    def process_multiple_tickers(self, tickers):
        """Process multiple tickers with batch control"""
        all_data = []
        total = len(tickers)
        
        print(f"\n📊 Processing {total} tickers...")
        
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{total}] Processing {ticker}...", end='')
            
            ticker_data = self.extract_kpi_data(ticker)
            
            if not ticker_data.empty:
                all_data.append(ticker_data)
                print(f" ✅ ({len(ticker_data)} data points)")
            else:
                print(f" ⚠️  (no data)")
            
            # Batch processing pause
            if i % self.batch_size == 0 and i < total:
                print(f"\n⏸️  Batch complete. Pausing for rate limit...")
                time.sleep(5)
                print("Resuming...\n")
        
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = self.calculate_growth_metrics(combined_df)
            return combined_df
        else:
            return pd.DataFrame()
    
    def export_data(self, df, filename_prefix='kpi_data'):
        """Export data to CSV with metadata"""
        if df.empty:
            logging.warning("No data to export")
            return None
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Drop the Period_Date column for cleaner export
        export_df = df.drop(columns=['Period_Date'], errors='ignore')
        
        # Save to CSV
        export_df.to_csv(filepath, index=False, encoding='utf-8')
        logging.info(f"Data exported to: {filepath}")
        
        # Create summary statistics
        summary = df.groupby(['Ticker', 'KPI_Label']).agg({
            'Value': ['count', 'mean', 'min', 'max', 'std'],
            'YoY_Growth': lambda x: x.dropna().mean() if len(x.dropna()) > 0 else np.nan
        }).round(3)
        
        summary_file = self.output_dir / f"summary_{timestamp}.csv"
        summary.to_csv(summary_file)
        
        # Create manifest
        manifest = {
            'created_at': datetime.now().isoformat(),
            'filename': filename,
            'tickers': df['Ticker'].unique().tolist(),
            'kpis': df['KPI_Label'].unique().tolist(),
            'periods': sorted(df['Period'].unique().tolist()),
            'statistics': {
                'total_records': len(df),
                'null_values': int(df['Value'].isna().sum()),
                'tickers_count': df['Ticker'].nunique(),
                'kpis_count': df['KPI_Label'].nunique(),
                'date_range': {
                    'start': str(df['Period_Date'].min()),
                    'end': str(df['Period_Date'].max())
                }
            }
        }
        
        with open(self.output_dir / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return filepath
    
    def create_streamlit_ready_export(self, df):
        """Create a Streamlit-optimized export"""
        if df.empty:
            return None
        
        # Pivot data for easier Streamlit visualization
        pivot_df = df.pivot_table(
            index=['Ticker', 'KPI_Label', 'Units', 'Category'],
            columns='Period',
            values='Value',
            aggfunc='first'
        ).reset_index()
        
        # Save pivot version
        pivot_file = self.output_dir / f"streamlit_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        pivot_df.to_csv(pivot_file, index=False)
        
        return pivot_file


def main():
    """Main execution function"""
    
    # Configuration
    TICKERS = [
        "AAPL US",
        "MSFT US", 
        "AMZN US",
        "GOOGL US",
        "META US",
        "TSLA US"
    ]
    
    print("\n🚀 Canalyst Python KPI Retrieval")
    print("=" * 50)
    
    # Initialize system
    retriever = CanalystKPIRetrieval()
    
    # Test connection
    if not retriever.test_connection():
        print("\n❌ Cannot proceed without valid connection")
        return
    
    print(f"\n📋 Ready to process {len(TICKERS)} tickers")
    print(f"📁 Output directory: {retriever.output_dir}")
    
    if input("\nProceed with data retrieval? (y/n): ").lower() != 'y':
        print("Cancelled by user")
        return
    
    # Process all tickers
    start_time = time.time()
    df = retriever.process_multiple_tickers(TICKERS)
    
    if df.empty:
        print("\n❌ No data retrieved")
        return
    
    # Export data
    csv_file = retriever.export_data(df)
    streamlit_file = retriever.create_streamlit_ready_export(df)
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n✅ Complete! Processed in {elapsed:.1f} seconds")
    print(f"\n📊 Summary:")
    print(f"  - Total records: {len(df):,}")
    print(f"  - Tickers processed: {df['Ticker'].nunique()}")
    print(f"  - KPIs extracted: {df['KPI_Label'].nunique()}")
    print(f"  - Missing values: {df['Value'].isna().sum()}")
    print(f"\n📁 Files created:")
    print(f"  - Main data: {csv_file}")
    print(f"  - Streamlit format: {streamlit_file}")
    print(f"  - Summary & manifest in: {retriever.output_dir}")
    
    # Show sample
    print("\n📋 Sample data:")
    sample = df[['Ticker', 'KPI_Label', 'Period', 'Value', 'YoY_Growth']].head(10)
    print(sample.to_string(index=False))


if __name__ == "__main__":
    # First install the package:
    # pip install canalyst-candas
    
    main()