import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file and environment variables"""
    
    # Load environment variables
    load_dotenv()
    
    # Load YAML config
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables if present
    if os.getenv('CANALYST_API_TOKEN'):
        config['api']['token'] = os.getenv('CANALYST_API_TOKEN')
    
    # Ensure required settings
    if not config.get('api', {}).get('token'):
        raise ValueError("CANALYST_API_TOKEN not found in config or environment")
    
    # Set defaults
    config.setdefault('paths', {})
    config['paths'].setdefault('output_dir', 'data/output')
    config['paths'].setdefault('csv_dir', 'data/csv')
    config['paths'].setdefault('log_dir', 'logs')
    
    config.setdefault('logging', {})
    config['logging'].setdefault('level', 'INFO')
    
    config.setdefault('scheduling', {})
    config['scheduling'].setdefault('time', '06:00')
    config['scheduling'].setdefault('timezone', 'US/Pacific')
    
    # Create directories
    for dir_key, dir_path in config['paths'].items():
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    return config