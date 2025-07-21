# tests/test_canalyst_client.py
import pytest
from unittest.mock import Mock, patch
from src.canalyst_client import CanalystClient

class TestCanalystClient:
    @pytest.fixture
    def client(self):
        config = {
            'api': {
                'base_url': 'https://api.canalyst.com/api',
                'timeout': 30,
                'rate_limit': {'requests_per_second': 5}
            }
        }
        with patch.dict('os.environ', {'CANALYST_API_TOKEN': 'test_token'}):
            return CanalystClient(config)
    
    def test_rate_limiting(self, client):
        """Test that rate limiting is enforced"""
        import time
        
        with patch.object(client.session, 'get') as mock_get:
            mock_get.return_value.json.return_value = {'results': []}
            
            start = time.time()
            for _ in range(5):
                client._make_request('/test')
            elapsed = time.time() - start
            
            # Should take at least 0.8 seconds for 5 requests at 5/sec
            assert elapsed >= 0.8
    
    def test_pagination_handling(self, client):
        """Test pagination is handled correctly"""
        # Mock paginated responses
        page1 = {
            'results': [{'id': 1}, {'id': 2}],
            'next': 'https://api.canalyst.com/api/test?cursor=abc'
        }
        page2 = {
            'results': [{'id': 3}, {'id': 4}],
            'next': None
        }
        
        with patch.object(client.session, 'get') as mock_get:
            mock_get.return_value.json.side_effect = [page1, page2]
            
            results = client.list_time_series('TEST123', 'Q1-2024.1')
            
            assert len(results) == 4
            assert results[0]['id'] == 1
            assert results[-1]['id'] == 4