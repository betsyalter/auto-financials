"""
KPI Service - Handles all data fetching and processing logic
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from loguru import logger
from ..models import DataPoint


class KPIService:
    """Service class for handling KPI data operations"""
    
    def __init__(self, canalyst_client, data_processor, company_mappings: pd.DataFrame):
        """
        Initialize KPI Service
        
        Args:
            canalyst_client: CanalystClient instance
            data_processor: KPIDataProcessor instance
            company_mappings: DataFrame with company mapping information
        """
        self.client = canalyst_client
        self.processor = data_processor
        self.company_mappings = company_mappings
    
    def search_company(self, ticker: str) -> Optional[Dict]:
        """
        Search for a company by ticker
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Company data dict or None if not found
        """
        # Check in mappings first
        company_row = self.company_mappings[
            self.company_mappings['search_ticker'] == ticker.upper()
        ]
        
        if not company_row.empty:
            return company_row.iloc[0].to_dict()
        
        # If not in mappings, try API search
        from ..csin_discovery import CSINDiscoveryTool
        discovery = CSINDiscoveryTool(self.client)
        
        for ticker_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
            companies = discovery.search_by_ticker(ticker, ticker_type)
            if companies:
                return companies[0]
        
        return None
    
    def get_available_metrics(self, company_id: str, model_version: str = None) -> Tuple[List[Dict], str]:
        """
        Get available metrics for a company
        
        Args:
            company_id: Company ID
            model_version: Model version (optional, fetches latest if not provided)
            
        Returns:
            Tuple of (metrics list, model version used)
        """
        # Get latest model if version not provided
        if not model_version:
            model = self.client.get_latest_equity_model(company_id)
            model_version = model['model_version']['name']
        
        # Get all time series
        all_time_series = self.client.list_time_series(company_id, model_version, is_kpi=None)
        
        # Filter to KPIs only
        kpis = [ts for ts in all_time_series if ts.get('kpi_data', {}).get('is_kpi', False)]
        
        return kpis, model_version
    
    def fetch_kpi_data(self, company_id: str, selected_kpis: pd.DataFrame, 
                       model_version: str) -> pd.DataFrame:
        """
        Fetch KPI data for a company
        
        Args:
            company_id: Company ID
            selected_kpis: DataFrame with selected KPIs
            model_version: Model version
            
        Returns:
            Processed DataFrame with KPI data
        """
        # Fetch historical data for each KPI
        historical_data = []
        for _, kpi in selected_kpis.iterrows():
            hist = self.client.get_historical_data_points(
                company_id,
                model_version,
                kpi['time_series_name']
            )
            historical_data.extend(hist)
        
        # Get historical periods
        hist_periods_data = self.client.get_historical_periods(company_id, model_version)
        
        # Package data for processor
        api_data = {
            'historical_data': historical_data,
            'forecast_data': [],  # No forecasts for now
            'periods': hist_periods_data,
            'time_series_info': selected_kpis.to_dict('records')
        }
        
        # Process the data
        df = self.processor.process_company_data(company_id, api_data, selected_kpis)
        
        return df
    
    def fetch_multi_company_data(self, companies_data: Dict[str, Dict], 
                                selected_kpis: List[Dict],
                                model_versions: Dict[str, str],
                                all_companies_metrics: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple companies
        
        Args:
            companies_data: Dict mapping ticker to company data
            selected_kpis: List of selected KPIs
            model_versions: Dict mapping ticker to model version
            all_companies_metrics: Dict mapping ticker to available metrics
            
        Returns:
            Dict mapping ticker to processed DataFrame
        """
        all_company_data = {}
        
        for ticker, company in companies_data.items():
            company_id = company['company_id']
            model_version = model_versions[ticker]
            
            # Get the specific metrics for this company
            company_metrics = all_companies_metrics[ticker]
            
            # Map selected KPIs to this company's metrics
            temp_kpis = []
            for i, selected_ts in enumerate(selected_kpis):
                # Find matching metric for this company
                matching_metric = next(
                    (m for m in company_metrics 
                     if m['description'].lower() == selected_ts['description'].lower()),
                    None
                )
                
                if matching_metric:
                    temp_kpis.append({
                        'company_id': company_id,
                        'time_series_name': matching_metric['names'][0],
                        'time_series_slug': matching_metric['slug'],
                        'kpi_label': matching_metric['description'],
                        'units': matching_metric['unit']['description'],
                        'category': matching_metric['category']['description'],
                        'all_names': ','.join(matching_metric['names']),
                        'priority': i + 1
                    })
            
            temp_kpi_df = pd.DataFrame(temp_kpis)
            
            # Fetch data for this company
            df = self.fetch_kpi_data(company_id, temp_kpi_df, model_version)
            all_company_data[ticker] = df
        
        return all_company_data
    
    def prepare_single_company_kpis(self, company_id: str, selected_kpis: List[Dict]) -> pd.DataFrame:
        """
        Prepare KPI mappings for a single company
        
        Args:
            company_id: Company ID
            selected_kpis: List of selected KPI dicts
            
        Returns:
            DataFrame with KPI mappings
        """
        temp_kpis = []
        for i, ts in enumerate(selected_kpis):
            temp_kpis.append({
                'company_id': company_id,
                'time_series_name': ts['names'][0],
                'time_series_slug': ts['slug'],
                'kpi_label': ts['description'],
                'units': ts['unit']['description'],
                'category': ts['category']['description'],
                'all_names': ','.join(ts['names']),
                'priority': i + 1
            })
        
        return pd.DataFrame(temp_kpis)
    
    def create_metric_groups(self, selected_kpis: List[str], 
                           all_companies_metrics: Dict[str, List],
                           group_name: str) -> Dict:
        """
        Create metric groups for multi-company comparison
        
        Args:
            selected_kpis: List of selected KPI names
            all_companies_metrics: Dict of company metrics
            group_name: Name for the metric group
            
        Returns:
            Metric group dict
        """
        group = {
            'name': group_name,
            'metrics': {}
        }
        
        # Build metrics mapping for each company
        for ticker, company_metrics in all_companies_metrics.items():
            matching_metrics = []
            
            for kpi_name in selected_kpis:
                # Find metric that matches the name
                for metric in company_metrics:
                    if metric['description'] == kpi_name:
                        matching_metrics.append(metric)
                        break
            
            if matching_metrics:
                group['metrics'][ticker] = matching_metrics
        
        return group
    
    def scale_to_millions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Scale large values to millions
        
        Args:
            df: DataFrame with financial data
            
        Returns:
            DataFrame with scaled values
        """
        # Identify which rows need scaling
        needs_scaling = {}
        
        for idx in df.index:
            if len(idx) == 4 and pd.isna(idx[3]):  # Base metric row
                row_values = df.loc[idx]
                # Check if any value >= 1M
                needs_scaling[idx] = any(
                    abs(val) >= 1000000 for val in row_values if pd.notna(val)
                )
        
        # Scale values
        scaled_df = df.copy()
        for idx in scaled_df.index:
            if len(idx) == 4 and pd.isna(idx[3]) and needs_scaling.get(idx, False):
                # Scale base metric values
                scaled_df.loc[idx] = scaled_df.loc[idx] / 1000000
        
        return scaled_df
    
    def filter_periods_by_type(self, df: pd.DataFrame, period_type: str) -> pd.DataFrame:
        """
        Filter DataFrame columns by period type
        
        Args:
            df: DataFrame with period columns
            period_type: 'annual' or 'quarterly'
            
        Returns:
            Filtered DataFrame
        """
        if period_type == 'annual':
            cols = [col for col in df.columns if col.startswith('FY')]
        else:  # quarterly
            cols = [col for col in df.columns if col.startswith('Q')]
        
        return df[cols]