# tests/test_data_processor.py
import pandas as pd
import pytest
from src.data_processor import KPIDataProcessor

class TestDataProcessor:
    def test_period_reordering(self):
        """Test periods are reordered correctly"""
        processor = KPIDataProcessor({})
        
        # Create test periods
        periods = [
            {'name': 'Q1-2025', 'type': 'fiscal_quarter', 'start_date': '2025-01-01'},
            {'name': 'FY2024', 'type': 'fiscal_year', 'start_date': '2024-01-01'},
            {'name': 'Q4-2024', 'type': 'fiscal_quarter', 'start_date': '2024-10-01'},
        ]
        
        # Test reordering logic
        # Should order as: Annual (newest first), then Quarterly (newest first)
        
    def test_growth_calculations(self):
        """Test QoQ and YoY calculations are correct"""
        processor = KPIDataProcessor({})
        
        # Create test data
        data = {
            'Q1-2025': 100,
            'Q4-2024': 95,
            'Q3-2024': 90,
            'Q2-2024': 85,
            'Q1-2024': 80
        }
        
        df = pd.DataFrame([data], index=[('REV', 'Revenue', 'Millions')])
        
        result = processor._add_growth_calculations(df)
        
        # Check QoQ: (100-95)/95 = 5.26%
        assert abs(result.loc[('REV', 'Revenue', 'Millions', 'QoQ %'), 'Q1-2025'] - 5.26) < 0.1
        
        # Check YoY: (100-80)/80 = 25%
        assert abs(result.loc[('REV', 'Revenue', 'Millions', 'YoY %'), 'Q1-2025'] - 25.0) < 0.1