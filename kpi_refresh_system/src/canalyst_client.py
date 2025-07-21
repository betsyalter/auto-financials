import requests
from typing import Dict, List, Optional
from datetime import datetime
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from dotenv import load_dotenv

load_dotenv()

class CanalystClient:
    def __init__(self, config: Dict):
        self.base_url = config['api']['base_url']
        self.timeout = config['api']['timeout']
        self.api_token = os.getenv('CANALYST_API_TOKEN')
        if not self.api_token:
            raise ValueError("CANALYST_API_TOKEN environment variable not set")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        })
        self._last_request_time = 0
        self._requests_per_second = config['api']['rate_limit']['requests_per_second']
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits (5 requests per second)"""
        elapsed = time.time() - self._last_request_time
        min_interval = 1.0 / self._requests_per_second
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request with retry logic"""
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making request to {url}")
        
        response = self.session.get(url, params=params, timeout=self.timeout)
        
        if response.status_code == 429:  # Too Many Requests
            retry_after = int(response.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited, waiting {retry_after} seconds")
            time.sleep(retry_after)
            raise Exception("Rate limited, retrying...")
        
        response.raise_for_status()
        return response.json()
    
    def get_company_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Get company info by Canalyst ticker (e.g., AAPL_US)"""
        response = self._make_request('/companies/', {
            'ticker_canalyst': ticker,
            'page_size': 1
        })
        
        results = response.get('results', [])
        return results[0] if results else None
    
    def get_latest_equity_model(self, company_id: str) -> Dict:
        """Get the latest equity model for a company_id"""
        # First, get the equity model series for this company
        series_response = self._make_request('/equity-model-series/', {'company_id': company_id})
        
        if not series_response.get('results'):
            raise ValueError(f"No equity model series found for company_id: {company_id}")
        
        # Get the first (should be only) series
        series = series_response['results'][0]
        series_id = series['self'].split('/')[-2]  # Extract ID from URL
        
        # Now get the latest model from this series
        return self._make_request(f'/equity-model-series/{series_id}/equity-models/latest/')
    
    def list_time_series(self, company_id: str, model_version: str, 
                        is_kpi: Optional[bool] = None) -> List[Dict]:
        """List all time series for an equity model"""
        # First get the series_id for this company
        series_response = self._make_request('/equity-model-series/', {'company_id': company_id})
        if not series_response.get('results'):
            raise ValueError(f"No equity model series found for company_id: {company_id}")
        
        series = series_response['results'][0]
        series_id = series['self'].split('/')[-2]  # Extract ID from URL
        
        params = {'page_size': 200}
        if is_kpi is not None:
            params['is_kpi'] = str(is_kpi).lower()
        
        all_results = []
        url = f'/equity-model-series/{series_id}/equity-models/{model_version}/time-series/'
        
        while url:
            if url.startswith('http'):
                # Full URL from pagination
                response = self.session.get(url, params=params, timeout=self.timeout)
                data = response.json()
            else:
                # Relative URL
                data = self._make_request(url, params)
            
            all_results.extend(data.get('results', []))
            url = data.get('next')
            params = {}  # Clear params for pagination
        
        return all_results
    
    def get_historical_data_points(self, company_id: str, model_version: str,
                                 time_series_name: str,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> List[Dict]:
        """Get historical data points for a specific time series"""
        # First get the series_id for this company
        series_response = self._make_request('/equity-model-series/', {'company_id': company_id})
        if not series_response.get('results'):
            raise ValueError(f"No equity model series found for company_id: {company_id}")
        
        series = series_response['results'][0]
        series_id = series['self'].split('/')[-2]  # Extract ID from URL
        
        params = {
            'time_series_name': time_series_name,
            'page_size': 500  # Max allowed
        }
        
        if start_date:
            params['period_min_start_date'] = start_date
        if end_date:
            params['period_max_end_date'] = end_date
        
        all_results = []
        url = f'/equity-model-series/{series_id}/equity-models/{model_version}/historical-data-points/'
        
        while url:
            if url.startswith('http'):
                response = self.session.get(url, params=params, timeout=self.timeout)
                data = response.json()
            else:
                data = self._make_request(url, params)
            
            all_results.extend(data.get('results', []))
            url = data.get('next')
            params = {}  # Clear params for pagination
        
        return all_results
    
    def get_forecast_data_points(self, company_id: str, model_version: str,
                               time_series_name: str) -> List[Dict]:
        """Get forecast data points for a specific time series"""
        # First get the series_id for this company
        series_response = self._make_request('/equity-model-series/', {'company_id': company_id})
        if not series_response.get('results'):
            raise ValueError(f"No equity model series found for company_id: {company_id}")
        
        series = series_response['results'][0]
        series_id = series['self'].split('/')[-2]  # Extract ID from URL
        
        # First, get the time series slug
        time_series_response = self._make_request(
            f'/equity-model-series/{series_id}/equity-models/{model_version}/time-series/{time_series_name}/'
        )
        
        time_series_slug = time_series_response['slug']
        
        # Then get forecast data points
        params = {'page_size': 200}
        all_results = []
        url = f'/equity-model-series/{series_id}/equity-models/{model_version}/time-series/{time_series_slug}/forecast-data-points/'
        
        while url:
            if url.startswith('http'):
                response = self.session.get(url, params=params, timeout=self.timeout)
                data = response.json()
            else:
                data = self._make_request(url, params)
            
            all_results.extend(data.get('results', []))
            url = data.get('next')
            params = {}
        
        return all_results
    
    def get_bulk_data(self, company_id: str, model_version: str, 
                     bulk_data_type: str = 'historical-data') -> str:
        """Get bulk data download URL"""
        # First get the series_id for this company
        series_response = self._make_request('/equity-model-series/', {'company_id': company_id})
        if not series_response.get('results'):
            raise ValueError(f"No equity model series found for company_id: {company_id}")
        
        series = series_response['results'][0]
        series_id = series['self'].split('/')[-2]  # Extract ID from URL
        
        response = self._make_request(
            f'/equity-model-series/{series_id}/equity-models/{model_version}/bulk-data/{bulk_data_type}/',
            {'format': 'csv'}
        )
        return response.get('data_files')
    
    def get_historical_periods(self, company_id: str, model_version: str) -> List[Dict]:
        """Get historical periods for a company's equity model"""
        # First get the series_id for this company
        series_response = self._make_request('/equity-model-series/', {'company_id': company_id})
        if not series_response.get('results'):
            raise ValueError(f"No equity model series found for company_id: {company_id}")
        
        series = series_response['results'][0]
        series_id = series['self'].split('/')[-2]  # Extract ID from URL
        
        response = self._make_request(
            f"/equity-model-series/{series_id}/equity-models/{model_version}/historical-periods/",
            {'page_size': 200}
        )
        return response.get('results', [])
    
    def get_forecast_periods(self, company_id: str, model_version: str) -> List[Dict]:
        """Get forecast periods for a company's equity model"""
        # First get the series_id for this company
        series_response = self._make_request('/equity-model-series/', {'company_id': company_id})
        if not series_response.get('results'):
            raise ValueError(f"No equity model series found for company_id: {company_id}")
        
        series = series_response['results'][0]
        series_id = series['self'].split('/')[-2]  # Extract ID from URL
        
        response = self._make_request(
            f"/equity-model-series/{series_id}/equity-models/{model_version}/forecast-periods/",
            {'page_size': 200}
        )
        return response.get('results', [])