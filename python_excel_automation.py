"""
Python Script to Automate Excel with Canalyst/Tegus Add-in
This uses Python to control Excel and execute TEGUS.CD formulas
"""

import win32com.client
import pandas as pd
import time
import os
from datetime import datetime
import logging
from pathlib import Path
import pythoncom

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ExcelCanalystAutomation:
    def __init__(self):
        """Initialize Excel automation with Canalyst"""
        # Initialize COM
        pythoncom.CoInitialize()
        
        # Create Excel instance
        self.excel = win32com.client.Dispatch("Excel.Application")
        self.excel.Visible = True  # Set to False for background processing
        self.excel.DisplayAlerts = False
        
        # Create or open workbook
        self.workbook = None
        self.setup_workbook()
        
    def setup_workbook(self):
        """Create a new workbook with required sheets"""
        self.workbook = self.excel.Workbooks.Add()
        
        # Create sheets
        self.data_sheet = self.workbook.Worksheets(1)
        self.data_sheet.Name = "Data_Retrieval"
        
        # Add config sheet
        self.config_sheet = self.workbook.Worksheets.Add()
        self.config_sheet.Name = "Config"
        
    def test_tegus_connection(self):
        """Test if TEGUS add-in is available"""
        try:
            test_cell = self.data_sheet.Range("A1")
            test_cell.Formula = '=TEGUS.CD("AAPL_US","MO_RIS_REV","FY24")'
            self.excel.Calculate()
            time.sleep(2)  # Wait for calculation
            
            result = test_cell.Value
            if result is None or str(result).startswith("#"):
                logging.error(f"TEGUS connection test failed. Result: {result}")
                return False
            else:
                logging.info(f"TEGUS connection successful. Test value: {result}")
                return True
                
        except Exception as e:
            logging.error(f"Error testing TEGUS: {str(e)}")
            return False
    
    def retrieve_single_value(self, ticker, kpi_code, period):
        """Retrieve a single KPI value using TEGUS.CD formula"""
        try:
            # Use a cell to execute the formula
            cell = self.data_sheet.Range("Z1")
            formula = f'=TEGUS.CD("{ticker}","{kpi_code}","{period}")'
            cell.Formula = formula
            
            # Wait for calculation
            self.excel.Calculate()
            time.sleep(0.5)  # Rate limiting
            
            # Get the value
            value = cell.Value
            
            # Clear the cell
            cell.Clear()
            
            return value
            
        except Exception as e:
            logging.error(f"Error retrieving {ticker}/{kpi_code}/{period}: {str(e)}")
            return None
    
    def retrieve_ticker_data(self, ticker, kpis, periods):
        """Retrieve all data for a single ticker"""
        logging.info(f"Processing ticker: {ticker}")
        
        data = []
        total_calls = len(kpis) * len(periods)
        current_call = 0
        
        for kpi in kpis:
            for period in periods:
                current_call += 1
                logging.info(f"  Retrieving {kpi['label']} for {period} ({current_call}/{total_calls})")
                
                value = self.retrieve_single_value(ticker, kpi['code'], period)
                
                data.append({
                    'Ticker': ticker,
                    'KPI_Code': kpi['code'],
                    'KPI_Label': kpi['label'],
                    'Units': kpi['units'],
                    'Category': kpi['category'],
                    'Period': period,
                    'Value': value,
                    'Retrieved_At': datetime.now()
                })
                
                # Rate limiting (60 calls per minute = 1 per second)
                time.sleep(1)
        
        return pd.DataFrame(data)
    
    def process_all_tickers(self, config):
        """Process all tickers and KPIs"""
        all_data = []
        
        # Generate periods
        periods = self.generate_periods()
        
        for ticker in config['tickers']:
            try:
                ticker_data = self.retrieve_ticker_data(
                    ticker, 
                    config['kpis'], 
                    periods
                )
                all_data.append(ticker_data)
                
                # Save intermediate results
                ticker_data.to_csv(f"temp_{ticker}.csv", index=False)
                
            except Exception as e:
                logging.error(f"Error processing {ticker}: {str(e)}")
                continue
        
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            return combined_df
        else:
            return pd.DataFrame()
    
    def generate_periods(self):
        """Generate period strings for annual and quarterly data"""
        current_year = datetime.now().year
        
        periods = []
        
        # Annual periods (FY24 to FY20)
        for year in range(current_year, current_year - 5, -1):
            periods.append(f"FY{year % 100}")
        
        # Quarterly periods (Q1-25 to Q2-22)
        for year in range(current_year + 1, current_year - 3, -1):
            for quarter in range(4, 0, -1):
                periods.append(f"Q{quarter}-{year % 100}")
                if len(periods) >= 17:  # 5 annual + 12 quarterly
                    break
            if len(periods) >= 17:
                break
        
        return periods
    
    def cleanup(self):
        """Clean up Excel instance"""
        try:
            if self.workbook:
                self.workbook.Close(SaveChanges=False)
            if self.excel:
                self.excel.Quit()
        except:
            pass
        finally:
            pythoncom.CoUninitialize()


def main():
    """Main execution"""
    # Configuration
    config = {
        'tickers': ['AAPL_US', 'MSFT_US', 'AMZN_US'],  # Add your tickers
        'kpis': [
            {'code': 'MO_RIS_REV', 'label': 'Revenue', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_GROSS_PROFIT', 'label': 'Gross Profit', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_OP_INC', 'label': 'Operating Income', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_NET_INC', 'label': 'Net Income', 'units': 'Millions', 'category': 'Income Statement'},
            {'code': 'MO_RIS_EPS', 'label': 'EPS', 'units': 'Per Share', 'category': 'Income Statement'}
        ]
    }
    
    automation = None
    
    try:
        # Initialize automation
        automation = ExcelCanalystAutomation()
        
        # Test connection
        if not automation.test_tegus_connection():
            logging.error("TEGUS add-in not available. Please ensure it's installed and you're logged in.")
            return
        
        # Process all data
        logging.info("Starting data retrieval...")
        df = automation.process_all_tickers(config)
        
        if not df.empty:
            # Save to CSV
            output_file = f"kpi_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(output_file, index=False)
            logging.info(f"Data saved to: {output_file}")
            
            # Display summary
            print("\nData retrieval complete!")
            print(f"Total records: {len(df)}")
            print(f"Tickers processed: {df['Ticker'].nunique()}")
            print(f"KPIs retrieved: {df['KPI_Code'].nunique()}")
            
            # Show sample
            print("\nSample data:")
            print(df.head(10))
            
        else:
            logging.error("No data retrieved")
            
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}")
        
    finally:
        if automation:
            automation.cleanup()


if __name__ == "__main__":
    # Install required package first:
    # pip install pywin32 pandas
    
    print("Excel-Canalyst Automation")
    print("=" * 50)
    print("This script will:")
    print("1. Open Excel in the background")
    print("2. Use TEGUS.CD formulas to retrieve data")
    print("3. Save results to CSV")
    print("\nMake sure:")
    print("- Canalyst/Tegus Excel add-in is installed")
    print("- You're logged into Canalyst")
    print("- Excel is not already running")
    print("=" * 50)
    
    if input("\nReady to start? (y/n): ").lower() == 'y':
        main()
    else:
        print("Cancelled by user")