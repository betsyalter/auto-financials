import click
from loguru import logger
import pandas as pd
from pathlib import Path
import sys
from typing import Optional, List
from datetime import datetime
from rich.prompt import Confirm
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.canalyst_client import CanalystClient
from src.data_processor import KPIDataProcessor
from src.excel_manager import ExcelManager
from src.csv_exporter import CSVExporter
from src.scheduler import KPIScheduler
from kpi_discovery import KPIDiscoveryTool
from csin_discovery import CSINDiscoveryTool
from src.utils.paths import resolve_path

class KPIRefreshApp:
    def __init__(self, config_path: str = None):
        # Use resolve_path for config file
        if config_path is None:
            config_path = str(resolve_path("kpi_refresh_system", "config", "config.yaml"))
        self.config = load_config(config_path)
        self.setup_logging()
        
        # Load mappings with resolve_path
        company_mappings_path = resolve_path("kpi_refresh_system", "config", "company_mappings.csv")
        if not company_mappings_path.exists():
            raise FileNotFoundError(
                f"company_mappings.csv not found at {company_mappings_path}. "
                "Make sure the file is committed to git and the path is correct."
            )
        self.company_mappings = pd.read_csv(company_mappings_path)
        
        kpi_mappings_path = resolve_path("kpi_refresh_system", "config", "kpi_mappings.csv")
        if not kpi_mappings_path.exists():
            raise FileNotFoundError(
                f"kpi_mappings.csv not found at {kpi_mappings_path}. "
                "Make sure the file is committed to git and the path is correct."
            )
        self.kpi_mappings = pd.read_csv(kpi_mappings_path)
        
        # Initialize components
        self.client = CanalystClient(self.config)
        self.processor = KPIDataProcessor(self.config)
        self.excel_manager = ExcelManager(self.config)
        self.csv_exporter = CSVExporter(self.config)
        
    def setup_logging(self):
        """Configure logging"""
        log_path = resolve_path('kpi_refresh_system', 'logs')
        log_path.mkdir(exist_ok=True)
        
        logger.add(
            log_path / 'kpi_refresh_{time}.log',
            rotation='1 day',
            retention='30 days',
            level=self.config.get('logging', {}).get('level', 'INFO')
        )
    
    def refresh_kpis(self, tickers: Optional[List[str]] = None):
        """Main refresh process"""
        logger.info("Starting KPI refresh process")
        
        # Filter companies to process
        if tickers:
            companies = self.company_mappings[
                self.company_mappings['search_ticker'].isin(tickers)
            ]
        else:
            companies = self.company_mappings
        
        logger.info(f"Processing {len(companies)} companies")
        
        all_company_data = {}
        errors = []
        
        for _, company in companies.iterrows():
            try:
                logger.info(f"Processing {company['search_ticker']} (Company ID: {company['company_id']})")
                
                # Get latest equity model
                model = self.client.get_latest_equity_model(company['company_id'])
                model_version = model['model_version']['name']
                
                # Get KPIs for this company
                company_kpis = self.kpi_mappings[
                    self.kpi_mappings['company_id'] == company['company_id']
                ]
                
                # Fetch data for each KPI
                historical_data = []
                
                for _, kpi in company_kpis.iterrows():
                    # Get historical data only
                    hist = self.client.get_historical_data_points(
                        company['company_id'],
                        model_version,
                        kpi['time_series_name']
                    )
                    # Debug: Check first data point
                    if hist and 'revenue' in kpi['time_series_name'].lower():
                        logger.info(f"Revenue data point units: {hist[0]['time_series']['unit']['description']}")
                    historical_data.extend(hist)
                
                # Get historical period information only
                hist_periods_data = self.client.get_historical_periods(company['company_id'], model_version)
                
                # Process data
                api_data = {
                    'historical_data': historical_data,
                    'forecast_data': [],  # Empty - no forecasts
                    'periods': hist_periods_data,  # Historical periods only
                    'time_series_info': company_kpis.to_dict('records')
                }
                
                df = self.processor.process_company_data(company['company_id'], api_data, company_kpis)
                all_company_data[company['company_id']] = df
                
                logger.success(f"Successfully processed {company['search_ticker']}")
                
            except Exception as e:
                logger.error(f"Error processing {company['search_ticker']}: {str(e)}")
                errors.append({'ticker': company['search_ticker'], 'error': str(e)})
        
        # Export results
        if all_company_data:
            # Excel export
            excel_path = self.excel_manager.create_kpi_workbook(
                all_company_data,
                self.company_mappings
            )
            logger.info(f"Created Excel workbook: {excel_path}")
            
            # CSV export
            csv_exports = self.csv_exporter.export_all_data(
                all_company_data,
                self.company_mappings,
                self.kpi_mappings
            )
            logger.info(f"Created CSV exports: {list(csv_exports.keys())}")
        
        # Report summary
        logger.info(f"Refresh complete. Processed: {len(all_company_data)}, Errors: {len(errors)}")
        
        if errors:
            error_df = pd.DataFrame(errors)
            error_path = resolve_path('kpi_refresh_system', 'logs') / f'errors_{datetime.now():%Y%m%d_%H%M%S}.csv'
            error_df.to_csv(error_path, index=False)
            logger.warning(f"Error details saved to {error_path}")

@click.group()
def cli():
    """KPI Refresh System - Canalyst/Tegus API Integration"""
    pass

@cli.command()
@click.option('--tickers', '-t', multiple=True, help='Specific tickers to refresh')
def refresh(tickers):
    """Run KPI refresh for all or specified tickers"""
    app = KPIRefreshApp()
    app.refresh_kpis(list(tickers) if tickers else None)

@cli.command()
def schedule():
    """Start scheduled refresh (daily at 6am PT)"""
    app = KPIRefreshApp()
    scheduler = KPIScheduler(app.config)
    
    logger.info("Starting scheduler...")
    scheduler.schedule_daily_refresh(app.refresh_kpis)
    scheduler.run_scheduler()

@cli.command()
@click.argument('ticker')
def test_ticker(ticker):
    """Test API connectivity for a single ticker"""
    app = KPIRefreshApp()
    
    # Find CSIN for ticker
    company = app.company_mappings[app.company_mappings['search_ticker'] == ticker]
    
    if company.empty:
        click.echo(f"Ticker {ticker} not found in mappings")
        return
    
    company_id = company.iloc[0]['company_id']
    click.echo(f"Testing {ticker} (Company ID: {company_id})")
    
    try:
        # Get latest model
        model = app.client.get_latest_equity_model(company_id)
        click.echo(f"Latest model: {model['model_version']['name']}")
        
        # Get time series
        time_series = app.client.list_time_series(
            company_id, 
            model['model_version']['name'],
            is_kpi=True
        )
        click.echo(f"Found {len(time_series)} KPI time series")
        
        # Show first few
        for ts in time_series[:5]:
            click.echo(f"  - {ts['names'][0]}: {ts['description']}")
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
def list_companies():
    """List all configured companies"""
    app = KPIRefreshApp()
    
    click.echo("Configured companies:")
    for _, company in app.company_mappings.iterrows():
        click.echo(f"  {company['search_ticker']}: {company['name']} (Company ID: {company['company_id']})")

@cli.command()
@click.argument('ticker')
def discover_kpis(ticker):
    """Interactively discover and select KPIs for a ticker"""
    app = KPIRefreshApp()
    discovery = KPIDiscoveryTool(app.client)
    
    # Find company
    company = app.company_mappings[app.company_mappings['search_ticker'] == ticker]
    if company.empty:
        click.echo(f"Ticker {ticker} not found in mappings")
        return
    
    company_id = company.iloc[0]['company_id']
    
    # Discover KPIs
    kpis = discovery.discover_company_kpis(ticker, company_id)
    
    # Interactive selection
    discovery.interactive_selection(ticker, company_id, kpis)
    
    # Export selections
    if discovery.selected_kpis:
        discovery.export_selections()

@cli.command()
def discover_all():
    """Discover KPIs for all configured companies"""
    app = KPIRefreshApp()
    discovery = KPIDiscoveryTool(app.client)
    
    for _, company in app.company_mappings.iterrows():
        if Confirm.ask(f"\nDiscover KPIs for {company['search_ticker']}?"):
            kpis = discovery.discover_company_kpis(company['search_ticker'], company['company_id'])
            discovery.interactive_selection(company['search_ticker'], company['company_id'], kpis)
    
    # Export all selections
    if discovery.selected_kpis:
        discovery.export_selections()

@cli.command()
@click.argument('ticker')
@click.option('--category', '-c', help='Filter by category')
@click.option('--search', '-s', help='Search term')
def list_kpis(ticker, category, search):
    """List available KPIs for a ticker"""
    app = KPIRefreshApp()
    
    # Find company
    company = app.company_mappings[app.company_mappings['search_ticker'] == ticker]
    if company.empty:
        click.echo(f"Ticker {ticker} not found")
        return
    
    company_id = company.iloc[0]['company_id']
    
    # Get latest model
    model = app.client.get_latest_equity_model(company_id)
    model_version = model['model_version']['name']
    
    # Get KPIs
    kpis = app.client.list_time_series(company_id, model_version, is_kpi=True)
    
    # Filter if needed
    if category:
        kpis = [k for k in kpis if category.lower() in k['category']['description'].lower()]
    
    if search:
        search_lower = search.lower()
        kpis = [k for k in kpis if 
                search_lower in k['description'].lower() or
                any(search_lower in name.lower() for name in k['names'])]
    
    # Display results
    click.echo(f"\nKPIs for {ticker} (Found: {len(kpis)})")
    click.echo("-" * 80)
    
    for kpi in sorted(kpis, key=lambda x: x['category']['description']):
        click.echo(f"\nCategory: {kpi['category']['description']}")
        click.echo(f"Name: {kpi['names'][0]}")
        click.echo(f"Description: {kpi['description']}")
        click.echo(f"Unit: {kpi['unit']['description']}")
        if len(kpi['names']) > 1:
            click.echo(f"Alt names: {', '.join(kpi['names'][1:])}")

@cli.command()
def explore_taxonomy():
    """Explore the names taxonomy (standardized metrics)"""
    app = KPIRefreshApp()
    
    # Get names taxonomy
    response = app.client._make_request('/names-taxonomy/', {
        'page_size': 200,
        'is_active': 'true'
    })
    
    names = response.get('results', [])
    
    # Group by section
    sections = {}
    for name in names:
        section = name.get('section', 'Other')
        if section not in sections:
            sections[section] = []
        sections[section].append(name)
    
    # Display
    click.echo("\nCanalyst Names Taxonomy")
    click.echo("=" * 80)
    
    for section, items in sorted(sections.items()):
        click.echo(f"\n{section} ({len(items)} items)")
        click.echo("-" * 40)
        
        for item in sorted(items, key=lambda x: x['name'])[:10]:  # Show first 10
            click.echo(f"  {item['name']}")
            if item.get('description'):
                click.echo(f"    → {item['description']}")
        
        if len(items) > 10:
            click.echo(f"  ... and {len(items) - 10} more")

@cli.command()
def discover_csin():
    """Interactive CSIN discovery tool"""
    app = KPIRefreshApp()
    discovery = CSINDiscoveryTool(app.client)
    discovery.interactive_search()

@cli.command()
@click.argument('ticker')
@click.option('--add', is_flag=True, help='Automatically add to company_mappings.csv')
def add_company(ticker, add):
    """Add a company to the system by ticker"""
    app = KPIRefreshApp()
    discovery = CSINDiscoveryTool(app.client)
    
    # Search for the company
    companies = None
    for ticker_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
        companies = discovery.search_by_ticker(ticker, ticker_type)
        if companies:
            click.echo(f"Found via {ticker_type} ticker")
            break
    
    if not companies:
        click.echo(f"No company found for ticker: {ticker}")
        return
    
    company = companies[0]
    csin = discovery._extract_csin(company)
    
    # Display found company
    click.echo(f"\nFound company:")
    click.echo(f"  Name: {company['name']}")
    click.echo(f"  Company ID: {company['company_id']}")
    click.echo(f"  CSIN: {csin}")
    click.echo(f"  Sector: {company.get('sector', {}).get('path', 'N/A')}")
    
    # Check if already exists
    existing = app.company_mappings[app.company_mappings['search_ticker'] == ticker.upper()]
    if not existing.empty:
        click.echo(f"\n⚠️  {ticker} already exists in company_mappings.csv")
        return
    
    # Add to mappings
    if add or click.confirm("\nAdd this company to company_mappings.csv?"):
        new_row = pd.DataFrame([{
            'search_ticker': ticker.upper(),
            'found_via': 'canalyst',
            'company_id': company['company_id'],
            'csin': csin,
            'name': company['name'],
            'ticker_canalyst': company.get('tickers', {}).get('Canalyst', ''),
            'ticker_bloomberg': company.get('tickers', {}).get('Bloomberg', ''),
            'sector': company.get('sector', {}).get('path', ''),
            'country': company.get('country_code', ''),
            'in_coverage': 'True' if company.get('is_in_coverage') else 'False'
        }])
        
        # Append to existing mappings
        updated_mappings = pd.concat([app.company_mappings, new_row], ignore_index=True)
        updated_mappings.to_csv(resolve_path('kpi_refresh_system', 'config', 'company_mappings.csv'), index=False)
        
        click.echo(f"\n✅ Successfully added {ticker} to company_mappings.csv")
        click.echo(f"\nNext steps:")
        click.echo(f"  1. Run: python main.py discover-kpis {ticker}")
        click.echo(f"  2. Run: python main.py refresh -t {ticker}")
    
@cli.command()
@click.argument('ticker')
@click.option('--type', '-t', default='auto', 
              help='Ticker type: auto, canalyst, bloomberg, capiq, factset, thomson')
def find_csin(ticker, type):
    """Find CSIN for a specific ticker"""
    app = KPIRefreshApp()
    discovery = CSINDiscoveryTool(app.client)
    
    if type == 'auto':
        # Try all ticker types
        for ticker_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
            companies = discovery.search_by_ticker(ticker, ticker_type)
            if companies:
                click.echo(f"\nFound via {ticker_type} ticker:")
                for company in companies:
                    csin = discovery._extract_csin(company)
                    click.echo(f"  {company['name']}")
                    click.echo(f"  Company ID: {company['company_id']}")
                    click.echo(f"  CSIN: {csin}")
                    click.echo(f"  Tickers: {json.dumps(company.get('tickers', {}))}")
                    click.echo("")
                break
        else:
            click.echo(f"No companies found for ticker: {ticker}")
    else:
        companies = discovery.search_by_ticker(ticker, type)
        if companies:
            for company in companies:
                csin = discovery._extract_csin(company)
                click.echo(f"\n{company['name']}")
                click.echo(f"Company ID: {company['company_id']}")
                click.echo(f"CSIN: {csin}")
                click.echo(f"Tickers: {json.dumps(company.get('tickers', {}))}")
        else:
            click.echo(f"No companies found")

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--ticker-column', '-c', default='ticker', help='Column name containing tickers')
@click.option('--type', '-t', default='auto', help='Ticker type to search')
def bulk_find_csin(input_file, ticker_column, type):
    """Bulk find CSINs from a file of tickers"""
    app = KPIRefreshApp()
    discovery = CSINDiscoveryTool(app.client)
    
    # Read input file
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    elif input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file)
    else:
        # Try to read as text file with one ticker per line
        with open(input_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        df = pd.DataFrame({ticker_column: tickers})
    
    if ticker_column not in df.columns:
        click.echo(f"Error: Column '{ticker_column}' not found. Available columns: {list(df.columns)}")
        return
    
    tickers = df[ticker_column].dropna().unique().tolist()
    click.echo(f"Searching for {len(tickers)} unique tickers...")
    
    # Search for CSINs
    results_df, not_found = discovery.bulk_search_tickers(tickers, type)
    
    # Save results
    if not results_df.empty:
        output_file = resolve_path('kpi_refresh_system', 'company_mappings_discovered.csv')
        results_df.to_csv(output_file, index=False)
        click.echo(f"\nResults saved to: {output_file}")
        
        # Show summary
        click.echo(f"\nSummary:")
        click.echo(f"  Found: {len(results_df)}")
        click.echo(f"  Not found: {len(not_found)}")
        
        if not_found:
            click.echo(f"\nTickers not found:")
            for ticker in not_found:
                click.echo(f"  - {ticker}")

@cli.command()
@click.option('--sector', '-s', help='Filter by sector')
@click.option('--country', '-c', help='Filter by country code') 
@click.option('--coverage', is_flag=True, help='Only show companies in coverage')
def list_available_companies(sector, country, coverage):
    """List all available companies"""
    app = KPIRefreshApp()
    
    params = {'page_size': 200}
    if sector:
        params['sector_path_contains'] = sector
    if country:
        params['country_code'] = country
    if coverage:
        params['is_in_coverage'] = 'true'
    
    response = app.client._make_request('/companies/', params)
    companies = response.get('results', [])
    
    click.echo(f"\nFound {len(companies)} companies")
    click.echo("-" * 80)
    
    for company in companies:
        click.echo(f"\n{company['name']}")
        click.echo(f"  Company ID: {company['company_id']}")
        
        tickers = company.get('tickers', {})
        if any(tickers.values()):
            click.echo(f"  Tickers:")
            for source, ticker in tickers.items():
                if ticker:
                    click.echo(f"    {source}: {ticker}")
        
        if company.get('sector'):
            click.echo(f"  Sector: {company['sector'].get('path', 'N/A')}")
        
        click.echo(f"  Country: {company.get('country_code', 'N/A')}")
        click.echo(f"  In Coverage: {'Yes' if company.get('is_in_coverage') else 'No'}")

if __name__ == '__main__':
    cli()