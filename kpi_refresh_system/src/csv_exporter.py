import pandas as pd
from pathlib import Path
from typing import Dict, List
import json
from datetime import datetime
from loguru import logger

class CSVExporter:
    def __init__(self, config: Dict):
        self.config = config
        self.output_path = Path(config['export']['csv_path'])
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def export_all_data(self, all_company_data: Dict[str, pd.DataFrame], 
                       company_mappings: pd.DataFrame,
                       kpi_mappings: pd.DataFrame) -> Dict[str, Path]:
        """
        Export all data in Streamlit-friendly format
        
        Returns:
            Dict mapping export type to file path
        """
        exports = {}
        
        # Export individual company files
        for company_id, df in all_company_data.items():
            ticker = company_mappings[company_mappings['company_id'] == company_id]['search_ticker'].iloc[0]
            exports[f'{ticker}_data'] = self._export_company_data(ticker, company_id, df)
        
        # Export consolidated data
        exports['all_companies'] = self._export_consolidated_data(
            all_company_data, company_mappings
        )
        
        # Export metadata
        exports['metadata'] = self._export_metadata(
            company_mappings, kpi_mappings, all_company_data
        )
        
        logger.info(f"Exported {len(exports)} files to {self.output_path}")
        
        return exports
    
    def _export_company_data(self, ticker: str, company_id: str, df: pd.DataFrame) -> Path:
        """Export single company data in long format"""
        
        # Convert from wide to long format
        long_data = []
        
        for idx, row in df.iterrows():
            # Parse index
            if isinstance(idx, tuple):
                if len(idx) == 3:  # Base data
                    kpi_code, kpi_desc, units = idx
                    metric_type = 'Value'
                elif len(idx) == 4:  # Growth data
                    kpi_code, kpi_desc, units, metric_type = idx
                    units = 'Percentage'
            
            # Process each period
            for period, value in row.items():
                if pd.notna(value):
                    # Determine period type
                    period_type = 'Annual' if period.startswith('FY') else 'Quarterly'
                    
                    long_data.append({
                        'ticker': ticker,
                        'company_id': company_id,
                        'kpi_code': kpi_code,
                        'kpi_description': kpi_desc,
                        'period': period,
                        'period_type': period_type,
                        'metric_type': metric_type,
                        'value': value,
                        'units': units,
                        'last_updated': datetime.now().isoformat()
                    })
        
        # Create DataFrame and save
        long_df = pd.DataFrame(long_data)
        filepath = self.output_path / f'{ticker}.csv'
        long_df.to_csv(filepath, index=False)
        
        return filepath
    
    def _export_consolidated_data(self, all_company_data: Dict[str, pd.DataFrame],
                                 company_mappings: pd.DataFrame) -> Path:
        """Export all companies in single file"""
        
        all_long_data = []
        
        for company_id, df in all_company_data.items():
            ticker = company_mappings[company_mappings['company_id'] == company_id]['search_ticker'].iloc[0]
            company_name = company_mappings[company_mappings['company_id'] == company_id]['name'].iloc[0]
            
            # Convert to long format (similar to above but include company name)
            for idx, row in df.iterrows():
                if isinstance(idx, tuple):
                    if len(idx) == 3:
                        kpi_code, kpi_desc, units = idx
                        metric_type = 'Value'
                    elif len(idx) == 4:
                        kpi_code, kpi_desc, units, metric_type = idx
                        units = 'Percentage'
                
                for period, value in row.items():
                    if pd.notna(value):
                        period_type = 'Annual' if period.startswith('FY') else 'Quarterly'
                        
                        all_long_data.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'company_id': company_id,
                            'kpi_code': kpi_code,
                            'kpi_description': kpi_desc,
                            'period': period,
                            'period_type': period_type,
                            'metric_type': metric_type,
                            'value': value,
                            'units': units,
                            'last_updated': datetime.now().isoformat()
                        })
        
        # Save consolidated file
        consolidated_df = pd.DataFrame(all_long_data)
        filepath = self.output_path / 'all_companies.csv'
        consolidated_df.to_csv(filepath, index=False)
        
        return filepath
    
    def _export_metadata(self, company_mappings: pd.DataFrame,
                        kpi_mappings: pd.DataFrame,
                        all_company_data: Dict) -> Path:
        """Export metadata for Streamlit app"""
        
        metadata = {
            'export_timestamp': datetime.now().isoformat(),
            'companies': company_mappings.to_dict('records'),
            'kpis': kpi_mappings.to_dict('records'),
            'summary': {
                'total_companies': len(company_mappings),
                'total_kpis': len(kpi_mappings),
                'data_points': sum(df.size for df in all_company_data.values()),
                'period_coverage': {
                    'annual_periods': 5,
                    'quarterly_periods': 12
                }
            }
        }
        
        filepath = self.output_path / 'metadata.json'
        with open(filepath, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return filepath