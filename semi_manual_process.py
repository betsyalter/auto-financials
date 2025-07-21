"""
Semi-Manual Process: Export from Excel, Process with Python
Step 1: You manually create Excel with TEGUS formulas
Step 2: This script processes the exported data
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
from pathlib import Path

class KPIProcessor:
    def __init__(self, input_file):
        """Initialize with Excel export file"""
        self.input_file = input_file
        self.output_dir = Path('./processed_data')
        self.output_dir.mkdir(exist_ok=True)
        
    def read_excel_export(self):
        """Read the manually exported Excel file"""
        # Read Excel file with all sheets
        excel_file = pd.ExcelFile(self.input_file)
        
        all_data = []
        
        # Process each ticker sheet
        for sheet_name in excel_file.sheet_names:
            if '_US' in sheet_name:  # Ticker sheets
                print(f"Processing sheet: {sheet_name}")
                
                # Read the sheet
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Add ticker column
                df['Ticker'] = sheet_name
                
                all_data.append(df)
        
        # Combine all ticker data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        return combined_df
    
    def transform_to_long_format(self, df):
        """Transform from wide to long format"""
        # Identify value columns (periods)
        period_columns = [col for col in df.columns if 
                         col.startswith('FY') or col.startswith('Q')]
        
        # Metadata columns
        id_vars = ['Ticker', 'KPI_Label', 'KPI_Code', 'Units', 'Category']
        
        # Melt the dataframe
        long_df = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=period_columns,
            var_name='Period',
            value_name='Value'
        )
        
        # Add period type
        long_df['Period_Type'] = long_df['Period'].apply(
            lambda x: 'Annual' if x.startswith('FY') else 'Quarterly'
        )
        
        return long_df
    
    def calculate_growth_metrics(self, df):
        """Calculate growth metrics"""
        # Sort for proper calculation
        df = df.sort_values(['Ticker', 'KPI_Code', 'Period'])
        
        # Calculate QoQ for quarterly data
        quarterly = df[df['Period_Type'] == 'Quarterly'].copy()
        quarterly['QoQ_Growth'] = (
            quarterly.groupby(['Ticker', 'KPI_Code'])['Value']
            .pct_change()
            .round(4)
        )
        
        # Calculate YoY
        annual = df[df['Period_Type'] == 'Annual'].copy()
        annual['YoY_Growth'] = (
            annual.groupby(['Ticker', 'KPI_Code'])['Value']
            .pct_change()
            .round(4)
        )
        
        # For quarterly YoY (compare to same quarter last year)
        quarterly['YoY_Growth'] = (
            quarterly.groupby(['Ticker', 'KPI_Code'])['Value']
            .pct_change(4)
            .round(4)
        )
        
        # Combine back
        df = pd.concat([annual, quarterly], ignore_index=True)
        
        return df
    
    def generate_summary_report(self, df):
        """Generate summary statistics"""
        summary = df.groupby(['Ticker', 'KPI_Label']).agg({
            'Value': ['min', 'max', 'mean', 'std', 'count'],
            'YoY_Growth': lambda x: x.dropna().mean() if len(x.dropna()) > 0 else np.nan
        }).round(3)
        
        summary.columns = ['Min', 'Max', 'Average', 'StdDev', 'Count', 'Avg_YoY_Growth']
        
        return summary
    
    def process_and_export(self):
        """Main processing function"""
        print("Reading Excel export...")
        df = self.read_excel_export()
        
        print("Transforming to long format...")
        df = self.transform_to_long_format(df)
        
        print("Calculating growth metrics...")
        df = self.calculate_growth_metrics(df)
        
        # Add timestamp
        df['Processed_At'] = datetime.now()
        
        # Export to CSV
        output_file = self.output_dir / f"kpi_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False)
        print(f"Data exported to: {output_file}")
        
        # Generate summary
        summary = self.generate_summary_report(df)
        summary_file = self.output_dir / "summary_report.csv"
        summary.to_csv(summary_file)
        print(f"Summary exported to: {summary_file}")
        
        # Display sample
        print("\nSample of processed data:")
        print(df.head(10))
        
        print("\nSummary statistics:")
        print(summary)
        
        return df


# Instructions for manual Excel setup
def print_excel_instructions():
    """Print instructions for manual Excel setup"""
    print("""
MANUAL EXCEL SETUP INSTRUCTIONS
===============================

1. Create Excel workbook with these sheets:
   - AAPL_US
   - MSFT_US
   - AMZN_US
   (one sheet per ticker)

2. In each ticker sheet, create this structure:

   Row 1: Headers
   A1: KPI_Label | B1: KPI_Code | C1: Units | D1: Category | E1: FY24 | F1: FY23 | G1: FY22 | etc...

3. Fill in KPI information:
   A2: Revenue | B2: MO_RIS_REV | C2: Millions | D2: Income Statement
   A3: Gross Profit | B3: MO_RIS_GROSS_PROFIT | C3: Millions | D3: Income Statement
   etc...

4. In cells E2, F2, G2, etc., enter TEGUS formulas:
   E2: =TEGUS.CD("AAPL_US", "MO_RIS_REV", "FY24")
   F2: =TEGUS.CD("AAPL_US", "MO_RIS_REV", "FY23")
   etc...

5. Copy formulas down for all KPIs

6. Once all formulas calculate, save as .xlsx file

7. Run this Python script to process the data!
""")


if __name__ == "__main__":
    print("Semi-Manual KPI Processing")
    print("=" * 50)
    
    # Check if user has the Excel file ready
    excel_file = input("Enter path to your Excel file (or 'help' for instructions): ").strip()
    
    if excel_file.lower() == 'help':
        print_excel_instructions()
    elif os.path.exists(excel_file):
        processor = KPIProcessor(excel_file)
        processor.process_and_export()
    else:
        print(f"File not found: {excel_file}")
        print("Run again with 'help' to see Excel setup instructions")