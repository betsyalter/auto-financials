"""
Canalyst/Tegus Data Automation
This script automates Excel to retrieve KPI data using TEGUS.CD formulas
"""

import win32com.client
import pandas as pd
import time
import os
from datetime import datetime
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('canalyst_automation.log'),
        logging.StreamHandler()
    ]
)

class CanalystAutomation:
    def __init__(self, visible=True):
        """
        Initialize the automation
        visible: Set to True to see Excel, False to run in background
        """
        logging.info("Starting Canalyst automation...")
        
        try:
            # Start Excel
            self.excel = win32com.client.Dispatch("Excel.Application")
            self.excel.Visible = visible
            self.excel.DisplayAlerts = False
            
            # Create a new workbook
            self.workbook = self.excel.Workbooks.Add()
            self.sheet = self.workbook.ActiveSheet
            self.sheet.Name = "Data"
            
            logging.info("Excel initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize Excel: {str(e)}")
            raise
    
    def test_canalyst_connection(self):
        """Test if Canalyst/Tegus add-in is working"""
        logging.info("Testing Canalyst connection...")
        
        try:
            # Try a simple formula
            self.sheet.Range("A1").Formula = '=TEGUS.CD("AAPL_US","MO_RIS_REV","FY24")'
            self.excel.Calculate()
            time.sleep(2)  # Wait for calculation
            
            result = self.sheet.Range("A1").Value
            self.sheet.Range("A1").Clear()
            
            if result is None or str(result).startswith("#"):
                logging.error(f"Canalyst test failed. Result: {result}")
                print("\n⚠️  Canalyst/Tegus add-in not working!")
                print("Please make sure:")
                print("1. The Tegus Excel add-in is installed")
                print("2. You are logged into Canalyst")
                print("3. Your subscription is active")
                return False
            else:
                logging.info(f"Canalyst connection successful! Test value: {result}")
                print(f"✅ Canalyst connection working! Test value: ${result:,.0f}")
                return True
                
        except Exception as e:
            logging.error(f"Connection test error: {str(e)}")
            return False
    
    def get_single_value(self, ticker, kpi_code, period):
        """Get a single KPI value"""
        try:
            # Use a temporary cell
            cell = self.sheet.Range("Z1")
            
            # Build and execute formula
            formula = f'=TEGUS.CD("{ticker}","{kpi_code}","{period}")'
            cell.Formula = formula
            
            # Wait for calculation
            self.excel.Calculate()
            time.sleep(0.5)  # Rate limiting
            
            # Get the result
            value = cell.Value
            
            # Clear the cell
            cell.Clear()
            
            # Handle errors
            if value is None or (isinstance(value, str) and value.startswith("#")):
                logging.warning(f"No data for {ticker}/{kpi_code}/{period}: {value}")
                return None
            
            return value
            
        except Exception as e:
            logging.error(f"Error getting value: {str(e)}")
            return None
    
    def get_kpi_data(self, ticker, kpi_config, periods):
        """Get all KPI data for a ticker"""
        logging.info(f"Processing {ticker}...")
        
        results = []
        total_items = len(kpi_config) * len(periods)
        current = 0
        
        for kpi in kpi_config:
            for period in periods:
                current += 1
                print(f"  [{current}/{total_items}] Getting {kpi['label']} for {period}...", end='\r')
                
                value = self.get_single_value(ticker, kpi['code'], period)
                
                results.append({
                    'Ticker': ticker,
                    'KPI_Code': kpi['code'],
                    'KPI_Label': kpi['label'],
                    'Units': kpi['units'],
                    'Category': kpi['category'],
                    'Period': period,
                    'Period_Type': 'Annual' if period.startswith('FY') else 'Quarterly',
                    'Value': value,
                    'Retrieved_At': datetime.now()
                })
        
        print(f"  ✅ Completed {ticker} - Retrieved {total_items} data points")
        return results
    
    def generate_periods(self):
        """Generate list of periods to retrieve"""
        periods = []
        current_year = datetime.now().year
        
        # Annual periods (FY24 to FY20)
        for year in range(current_year, current_year - 5, -1):
            periods.append(f"FY{year % 100}")
        
        # Quarterly periods (last 12 quarters)
        quarters_added = 0
        for year in range(current_year + 1, current_year - 3, -1):
            for quarter in [4, 3, 2, 1]:
                if quarters_added < 12:
                    periods.append(f"Q{quarter}-{year % 100}")
                    quarters_added += 1
        
        return periods
    
    def process_all_data(self, tickers, kpi_config):
        """Process all tickers and KPIs"""
        all_data = []
        periods = self.generate_periods()
        
        print(f"\n📊 Processing {len(tickers)} tickers with {len(kpi_config)} KPIs...")
        print(f"📅 Periods: {periods[:5]}... ({len(periods)} total)\n")
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] {ticker}")
            
            ticker_data = self.get_kpi_data(ticker, kpi_config, periods)
            all_data.extend(ticker_data)
            
            # Small pause between tickers
            if i < len(tickers):
                time.sleep(2)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        # Calculate growth metrics
        df = self.calculate_growth_metrics(df)
        
        return df
    
    def calculate_growth_metrics(self, df):
        """Add growth calculations"""
        # Sort data properly
        df = df.sort_values(['Ticker', 'KPI_Code', 'Period_Type', 'Period'])
        
        # Create separate groups for calculations
        for ticker in df['Ticker'].unique():
            for kpi in df['KPI_Code'].unique():
                # Annual YoY
                mask = (df['Ticker'] == ticker) & (df['KPI_Code'] == kpi) & (df['Period_Type'] == 'Annual')
                if mask.any():
                    df.loc[mask, 'YoY_Growth'] = df.loc[mask, 'Value'].pct_change()
                
                # Quarterly QoQ
                mask = (df['Ticker'] == ticker) & (df['KPI_Code'] == kpi) & (df['Period_Type'] == 'Quarterly')
                if mask.any():
                    df.loc[mask, 'QoQ_Growth'] = df.loc[mask, 'Value'].pct_change()
                    # Quarterly YoY (4 quarters back)
                    df.loc[mask, 'YoY_Growth'] = df.loc[mask, 'Value'].pct_change(4)
        
        return df
    
    def save_results(self, df, output_dir='./output'):
        """Save results to CSV"""
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save main data file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'kpi_data_{timestamp}.csv'
        filepath = output_path / filename
        
        df.to_csv(filepath, index=False)
        logging.info(f"Data saved to: {filepath}")
        
        # Create summary
        summary = df.groupby(['Ticker', 'KPI_Label']).agg({
            'Value': ['count', 'mean', 'std'],
            'YoY_Growth': lambda x: x.dropna().mean()
        }).round(3)
        
        summary_file = output_path / f'summary_{timestamp}.csv'
        summary.to_csv(summary_file)
        
        # Create manifest
        manifest = {
            'created_at': datetime.now().isoformat(),
            'filename': filename,
            'tickers': df['Ticker'].unique().tolist(),
            'kpis': df['KPI_Label'].unique().tolist(),
            'periods': df['Period'].unique().tolist(),
            'total_records': len(df),
            'null_values': int(df['Value'].isna().sum())
        }
        
        import json
        with open(output_path / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return filepath
    
    def cleanup(self):
        """Close Excel properly"""
        try:
            self.workbook.Close(SaveChanges=False)
            self.excel.Quit()
            logging.info("Excel closed successfully")
        except:
            pass


def main():
    """Main execution function"""
    
    # Configuration - CUSTOMIZE THESE!
    TICKERS = [
        'AAPL_US',
        'MSFT_US',
        'AMZN_US',
        'META_US'
    ]
    
    KPI_CONFIG = [
        {'code': 'MO_RIS_REV', 'label': 'Revenue', 'units': 'Millions', 'category': 'Income Statement'},
        {'code': 'MO_RIS_GROSS_PROFIT', 'label': 'Gross Profit', 'units': 'Millions', 'category': 'Income Statement'},
        {'code': 'MO_RIS_OP_INC', 'label': 'Operating Income', 'units': 'Millions', 'category': 'Income Statement'},
        {'code': 'MO_RIS_NET_INC', 'label': 'Net Income', 'units': 'Millions', 'category': 'Income Statement'},
        {'code': 'MO_RIS_EPS', 'label': 'EPS', 'units': 'Per Share', 'category': 'Income Statement'}
    ]
    
    print("\n🚀 Canalyst Data Automation")
    print("=" * 50)
    
    automation = None
    
    try:
        # Initialize automation
        show_excel = input("Show Excel window? (y/n, default=y): ").lower() != 'n'
        automation = CanalystAutomation(visible=show_excel)
        
        # Test connection
        if not automation.test_canalyst_connection():
            print("\n❌ Cannot proceed without Canalyst connection.")
            return
        
        print("\n✅ Ready to retrieve data!")
        print(f"Tickers: {', '.join(TICKERS)}")
        print(f"KPIs: {len(KPI_CONFIG)}")
        
        if input("\nProceed? (y/n): ").lower() != 'y':
            print("Cancelled by user")
            return
        
        # Process all data
        start_time = time.time()
        df = automation.process_all_data(TICKERS, KPI_CONFIG)
        
        # Save results
        output_file = automation.save_results(df)
        
        # Summary
        elapsed = time.time() - start_time
        print(f"\n✅ Complete! Processed in {elapsed:.1f} seconds")
        print(f"📁 Data saved to: {output_file}")
        print(f"📊 Total records: {len(df)}")
        print(f"⚠️  Missing values: {df['Value'].isna().sum()}")
        
        # Show sample
        print("\n📋 Sample data:")
        print(df[['Ticker', 'KPI_Label', 'Period', 'Value']].head(10))
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        
    finally:
        if automation:
            automation.cleanup()
        print("\n👋 Done!")


if __name__ == "__main__":
    main()