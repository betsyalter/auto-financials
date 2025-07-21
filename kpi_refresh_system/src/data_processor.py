import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from loguru import logger
from src.models import DataPoint, Period, TimeSeries

class KPIDataProcessor:
    def __init__(self, config: Dict):
        self.config = config
        
    def process_company_data(self, company_id: str, api_data: Dict, kpi_mappings: pd.DataFrame = None) -> pd.DataFrame:
        """
        Process raw API data into structured DataFrame
        
        Args:
            company_id: Company ID
            api_data: Dict containing:
                - historical_data: List of historical data points
                - forecast_data: List of forecast data points
                - time_series_info: Time series metadata
                - periods: Period information
        
        Returns:
            DataFrame with KPIs as rows and periods as columns
        """
        # Create period mapping
        periods_df = self._create_periods_dataframe(api_data['periods'])
        
        # Process data points
        all_data_points = []
        
        # Create units lookup from kpi_mappings if provided
        units_lookup = {}
        if kpi_mappings is not None:
            for _, kpi in kpi_mappings.iterrows():
                units_lookup[kpi['time_series_name']] = kpi['units']
        
        # Historical data
        for dp in api_data['historical_data']:
            time_series_name = dp['time_series']['names'][0]
            # Use units from kpi_mappings if available, otherwise from API
            units = units_lookup.get(time_series_name, dp['time_series']['unit']['description'])
            
            # Process value
            value = None
            if dp['value']:
                value = float(dp['value'])
                # If value has more than 6 digits, divide by 1,000,000
                if abs(value) >= 1000000:  # 1 million or more
                    value = value / 1000000
            
            all_data_points.append({
                'time_series': time_series_name,  # Primary name
                'time_series_desc': dp['time_series']['description'],
                'period': dp['period']['name'],
                'value': value,
                'is_forecast': False,
                'units': units
            })
        
        # Forecast data  
        for dp in api_data['forecast_data']:
            all_data_points.append({
                'time_series': dp['time_series']['names'][0],
                'time_series_desc': dp['time_series']['description'],
                'period': dp['period']['name'],
                'value': float(dp['value']) if dp['value'] else None,
                'is_forecast': True,
                'units': dp['time_series']['unit']['description']
            })
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data_points)
        
        # Pivot to wide format
        pivot_df = df.pivot_table(
            index=['time_series', 'time_series_desc', 'units'],
            columns='period',
            values='value',
            aggfunc='first'
        )
        
        # Reorder columns chronologically
        pivot_df = self._reorder_periods(pivot_df, periods_df)
        
        # Calculate growth metrics
        pivot_df = self._add_growth_calculations(pivot_df)
        
        return pivot_df
    
    def _create_periods_dataframe(self, periods: List[Dict]) -> pd.DataFrame:
        """Create DataFrame of periods with proper ordering"""
        period_data = []
        
        for period in periods:
            period_data.append({
                'name': period['name'],
                'type': period['period_duration_type'],
                'start_date': pd.to_datetime(period['start_date']),
                'end_date': pd.to_datetime(period['end_date']),
                'is_forecast': period.get('is_forecast', False)
            })
        
        df = pd.DataFrame(period_data)
        df = df.sort_values('start_date')
        
        return df
    
    def _reorder_periods(self, df: pd.DataFrame, periods_df: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns to match requirement: Annual (FY24-FY20), then Quarterly (Q1-25 to Q2-22)"""
        
        # Separate annual and quarterly periods
        annual_periods = periods_df[periods_df['type'] == 'fiscal_year']['name'].tolist()
        quarterly_periods = periods_df[periods_df['type'] == 'fiscal_quarter']['name'].tolist()
        
        # Reverse annual periods (most recent first)
        annual_periods = annual_periods[::-1][:5]  # Last 5 years
        
        # Take most recent 12 quarters
        quarterly_periods = quarterly_periods[::-1][:12]
        
        # Combine in required order
        ordered_columns = annual_periods + quarterly_periods
        
        # Filter to columns that exist
        ordered_columns = [col for col in ordered_columns if col in df.columns]
        
        return df[ordered_columns]
    
    def _add_growth_calculations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add QoQ and YoY growth calculations"""
        
        # Identify annual and quarterly columns
        annual_cols = [col for col in df.columns if col.startswith('FY')]
        quarterly_cols = [col for col in df.columns if col.startswith('Q')]
        
        # Create new DataFrame with growth rows
        growth_rows = []
        
        for idx, row in df.iterrows():
            # Original row
            growth_rows.append(row)
            
            # QoQ growth row (only for quarterly data)
            qoq_row = pd.Series(index=df.columns, name=idx + ('qoq growth',))
            for i in range(1, len(quarterly_cols)):
                curr_col = quarterly_cols[i-1]  # More recent quarter
                prev_col = quarterly_cols[i]    # Previous quarter
                if pd.notna(row[curr_col]) and pd.notna(row[prev_col]) and row[prev_col] != 0:
                    qoq_row[curr_col] = ((row[curr_col] - row[prev_col]) / abs(row[prev_col])) * 100
            growth_rows.append(qoq_row)
            
            # YoY growth row
            yoy_row = pd.Series(index=df.columns, name=idx + ('yoy growth',))
            
            # Annual YoY (comparing consecutive years)
            for i in range(1, len(annual_cols)):
                curr_col = annual_cols[i-1]  # More recent year
                prev_col = annual_cols[i]    # Previous year
                if pd.notna(row[curr_col]) and pd.notna(row[prev_col]) and row[prev_col] != 0:
                    yoy_row[curr_col] = ((row[curr_col] - row[prev_col]) / abs(row[prev_col])) * 100
            
            # Quarterly YoY (comparing same quarter previous year)
            if len(quarterly_cols) >= 4:
                for i in range(min(8, len(quarterly_cols))):
                    if i + 4 < len(quarterly_cols):
                        curr_col = quarterly_cols[i]      # Current quarter
                        prev_col = quarterly_cols[i + 4]  # Same quarter last year
                        if pd.notna(row[curr_col]) and pd.notna(row[prev_col]) and row[prev_col] != 0:
                            yoy_row[curr_col] = ((row[curr_col] - row[prev_col]) / abs(row[prev_col])) * 100
            growth_rows.append(yoy_row)
        
        # Combine all rows
        result_df = pd.DataFrame(growth_rows)
        
        return result_df
    
    def convert_units(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert between units (e.g., thousands to millions)"""
        conversions = {
            ('Thousands', 'Millions'): 0.001,
            ('Units', 'Millions'): 0.000001,
            ('Basis Points', 'Percentage'): 0.01,
        }
        
        key = (from_unit, to_unit)
        if key in conversions:
            return value * conversions[key]
        
        return value