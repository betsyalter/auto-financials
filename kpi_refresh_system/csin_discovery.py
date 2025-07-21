import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import pandas as pd
from typing import List, Dict, Optional
import json
from pathlib import Path
from src.canalyst_client import CanalystClient
from loguru import logger
import csv

console = Console()

class CSINDiscoveryTool:
    def __init__(self, client: CanalystClient):
        self.client = client
        self.discovered_companies = []
        
    def search_by_ticker(self, ticker: str, ticker_type: str = 'canalyst') -> List[Dict]:
        """
        Search for companies by ticker
        
        Args:
            ticker: The ticker symbol (e.g., 'AAPL')
            ticker_type: One of 'canalyst', 'bloomberg', 'capiq', 'factset', 'thomson'
        """
        # Map ticker type to API parameter
        ticker_params = {
            'canalyst': 'ticker_canalyst',
            'bloomberg': 'ticker_bloomberg',
            'capiq': 'ticker_capiq',
            'factset': 'ticker_factset',
            'thomson': 'ticker_thomson'
        }
        
        param_name = ticker_params.get(ticker_type, 'ticker_canalyst')
        
        console.print(f"\n[bold blue]Searching for {ticker} ({ticker_type} ticker)...[/bold blue]")
        
        response = self.client._make_request('/companies/', {
            param_name: ticker,
            'page_size': 50
        })
        
        companies = response.get('results', [])
        
        if not companies:
            # Try with common suffixes
            suffixes = ['_US', '_CN', '_CA', '_GB', ' US', ' CN', ' CA', ' GB']
            for suffix in suffixes:
                response = self.client._make_request('/companies/', {
                    param_name: ticker + suffix,
                    'page_size': 50
                })
                companies = response.get('results', [])
                if companies:
                    break
        
        return companies
    
    def search_by_name(self, company_name: str) -> List[Dict]:
        """Search for companies by name"""
        console.print(f"\n[bold blue]Searching for '{company_name}'...[/bold blue]")
        
        # Try exact match first
        response = self.client._make_request('/companies/', {
            'name': company_name,
            'page_size': 50
        })
        
        companies = response.get('results', [])
        
        # If no exact match, try contains
        if not companies:
            response = self.client._make_request('/companies/', {
                'name_contains': company_name,
                'page_size': 50
            })
            companies = response.get('results', [])
        
        return companies
    
    def search_by_sector(self, sector: str) -> List[Dict]:
        """Search for companies by sector"""
        response = self.client._make_request('/companies/', {
            'sector_path_contains': sector,
            'is_in_coverage': 'true',
            'page_size': 200
        })
        
        return response.get('results', [])
    
    def bulk_search_tickers(self, ticker_list: List[str], ticker_type: str = 'auto') -> pd.DataFrame:
        """
        Bulk search for multiple tickers
        
        Args:
            ticker_list: List of tickers to search
            ticker_type: 'auto' to try all types, or specific type
        """
        results = []
        not_found = []
        
        with console.status("[bold green]Searching for companies...") as status:
            for i, ticker in enumerate(ticker_list):
                status.update(f"[bold green]Searching {i+1}/{len(ticker_list)}: {ticker}")
                
                if ticker_type == 'auto':
                    # Try different ticker types
                    found = False
                    for t_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
                        companies = self.search_by_ticker(ticker, t_type)
                        if companies:
                            # Take the first match
                            company = companies[0]
                            results.append({
                                'search_ticker': ticker,
                                'found_via': t_type,
                                'company_id': company['company_id'],
                                'csin': self._extract_csin(company),
                                'name': company['name'],
                                'ticker_canalyst': company['tickers'].get('Canalyst', ''),
                                'ticker_bloomberg': company['tickers'].get('Bloomberg', ''),
                                'sector': company.get('sector', {}).get('path', '') if company.get('sector') else '',
                                'country': company.get('country_code', ''),
                                'in_coverage': company.get('is_in_coverage', False)
                            })
                            found = True
                            break
                    
                    if not found:
                        not_found.append(ticker)
                else:
                    # Search specific ticker type
                    companies = self.search_by_ticker(ticker, ticker_type)
                    if companies:
                        company = companies[0]
                        results.append({
                            'search_ticker': ticker,
                            'found_via': ticker_type,
                            'company_id': company['company_id'],
                            'csin': self._extract_csin(company),
                            'name': company['name'],
                            'ticker_canalyst': company['tickers'].get('Canalyst', ''),
                            'ticker_bloomberg': company['tickers'].get('Bloomberg', ''),
                            'sector': company.get('sector', {}).get('path', '') if company.get('sector') else '',
                            'country': company.get('country_code', ''),
                            'in_coverage': company.get('is_in_coverage', False)
                        })
                    else:
                        not_found.append(ticker)
        
        # Create DataFrame
        df = pd.DataFrame(results)
        
        # Report results
        console.print(f"\n[bold green]Found {len(results)} companies[/bold green]")
        if not_found:
            console.print(f"[bold red]Not found: {', '.join(not_found)}[/bold red]")
        
        return df, not_found
    
    def _extract_csin(self, company: Dict) -> str:
        """Extract CSIN from company data"""
        # Get primary equity model series
        ems_url = company.get('equity_model_series_set', '')
        
        if ems_url:
            # Fetch equity model series
            response = self.client.session.get(ems_url + '?is_primary=true', timeout=30)
            if response.ok:
                data = response.json()
                results = data.get('results', [])
                if results:
                    return results[0]['csin']
        
        # If can't get CSIN, return company_id with suffix
        return f"{company['company_id']}0124"  # Default suffix
    
    def interactive_search(self):
        """Interactive CSIN discovery interface"""
        discovered = []
        
        while True:
            console.clear()
            console.print("[bold]CSIN Discovery Tool[/bold]\n")
            console.print(f"Discovered: {len(discovered)} companies\n")
            
            options = [
                "1. Search by ticker symbol",
                "2. Search by company name", 
                "3. Bulk import from file",
                "4. Search by sector",
                "5. View discovered companies",
                "6. Export results",
                "7. Exit"
            ]
            
            for option in options:
                console.print(f"  {option}")
            
            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5", "6", "7"])
            
            if choice == "1":
                self._search_ticker_interactive(discovered)
            elif choice == "2":
                self._search_name_interactive(discovered)
            elif choice == "3":
                self._bulk_import_interactive(discovered)
            elif choice == "4":
                self._search_sector_interactive(discovered)
            elif choice == "5":
                self._view_discovered(discovered)
            elif choice == "6":
                self._export_results(discovered)
            elif choice == "7":
                break
    
    def _search_ticker_interactive(self, discovered: List[Dict]):
        """Interactive ticker search"""
        ticker = Prompt.ask("\nEnter ticker symbol").upper()
        
        # Ask for ticker type
        ticker_type = Prompt.ask(
            "Ticker type",
            choices=["auto", "canalyst", "bloomberg", "capiq", "factset", "thomson"],
            default="auto"
        )
        
        if ticker_type == "auto":
            # Try all types
            for t_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
                companies = self.search_by_ticker(ticker, t_type)
                if companies:
                    console.print(f"\n[green]Found via {t_type} ticker[/green]")
                    self._display_companies(companies)
                    
                    if len(companies) == 1:
                        if Confirm.ask("Add this company?"):
                            discovered.append(self._company_to_record(companies[0], ticker, t_type))
                    else:
                        idx = Prompt.ask("Select company (number) or 'skip'")
                        if idx.isdigit() and 0 < int(idx) <= len(companies):
                            discovered.append(self._company_to_record(companies[int(idx)-1], ticker, t_type))
                    break
            else:
                console.print(f"[red]No results found for {ticker}[/red]")
        else:
            companies = self.search_by_ticker(ticker, ticker_type)
            if companies:
                self._display_companies(companies)
                if len(companies) == 1:
                    if Confirm.ask("Add this company?"):
                        discovered.append(self._company_to_record(companies[0], ticker, ticker_type))
                else:
                    idx = Prompt.ask("Select company (number) or 'skip'")
                    if idx.isdigit() and 0 < int(idx) <= len(companies):
                        discovered.append(self._company_to_record(companies[int(idx)-1], ticker, ticker_type))
            else:
                console.print(f"[red]No results found[/red]")
        
        input("\nPress Enter to continue...")
    
    def _display_companies(self, companies: List[Dict]):
        """Display company search results"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", width=3)
        table.add_column("Name", width=40)
        table.add_column("ID", width=10)
        table.add_column("Tickers", width=30)
        table.add_column("Sector", width=25)
        table.add_column("Coverage", width=8)
        
        for i, company in enumerate(companies, 1):
            tickers = company.get('tickers', {})
            ticker_str = ", ".join([f"{k}:{v}" for k, v in tickers.items() if v])[:30]
            
            sector = "N/A"
            if company.get('sector'):
                sector = company['sector'].get('name', 'N/A')
            
            table.add_row(
                str(i),
                company['name'][:40],
                company['company_id'],
                ticker_str,
                sector[:25],
                "✓" if company.get('is_in_coverage') else "✗"
            )
        
        console.print(table)
    
    def _company_to_record(self, company: Dict, search_ticker: str, found_via: str) -> Dict:
        """Convert company object to record for storage"""
        return {
            'search_ticker': search_ticker,
            'found_via': found_via,
            'company_id': company['company_id'],
            'csin': self._extract_csin(company),
            'company_name': company['name'],
            'ticker_canalyst': company['tickers'].get('Canalyst', ''),
            'ticker_bloomberg': company['tickers'].get('Bloomberg', ''),
            'ticker_capiq': company['tickers'].get('CapIQ', ''),
            'ticker_factset': company['tickers'].get('FactSet', ''),
            'ticker_thomson': company['tickers'].get('Thomson', ''),
            'sector': company.get('sector', {}).get('path', '') if company.get('sector') else '',
            'country': company.get('country_code', ''),
            'in_coverage': company.get('is_in_coverage', False)
        }
    
    def _search_name_interactive(self, discovered: List[Dict]):
        """Interactive company name search"""
        name = Prompt.ask("\nEnter company name (or part of name)")
        
        companies = self.search_by_name(name)
        if companies:
            self._display_companies(companies)
            if len(companies) == 1:
                if Confirm.ask("Add this company?"):
                    discovered.append(self._company_to_record(companies[0], name, "name_search"))
            else:
                idx = Prompt.ask("Select company (number) or 'skip'")
                if idx.isdigit() and 0 < int(idx) <= len(companies):
                    discovered.append(self._company_to_record(companies[int(idx)-1], name, "name_search"))
        else:
            console.print(f"[red]No results found[/red]")
        
        input("\nPress Enter to continue...")
    
    def _bulk_import_interactive(self, discovered: List[Dict]):
        """Bulk import tickers from file"""
        file_path = Prompt.ask("\nEnter path to ticker file (CSV or TXT)")
        
        if not Path(file_path).exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            input("Press Enter to continue...")
            return
        
        # Read tickers
        tickers = []
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            # Assume first column contains tickers
            tickers = df.iloc[:, 0].dropna().tolist()
        else:
            with open(file_path, 'r') as f:
                tickers = [line.strip() for line in f if line.strip()]
        
        console.print(f"\nFound {len(tickers)} tickers to search")
        
        if Confirm.ask("Proceed with bulk search?"):
            df, not_found = self.bulk_search_tickers(tickers)
            
            # Convert to records and add to discovered
            for _, row in df.iterrows():
                discovered.append(row.to_dict())
            
            console.print(f"\n[green]Added {len(df)} companies[/green]")
            
        input("\nPress Enter to continue...")
    
    def _search_sector_interactive(self, discovered: List[Dict]):
        """Search companies by sector"""
        sector = Prompt.ask("\nEnter sector keyword (e.g., 'Technology', 'Healthcare')")
        
        companies = self.search_by_sector(sector)
        if companies:
            console.print(f"\nFound {len(companies)} companies in {sector}")
            self._display_companies(companies[:20])  # Show first 20
            
            if len(companies) > 20:
                console.print(f"\n... and {len(companies) - 20} more")
            
            if Confirm.ask("\nAdd all companies?"):
                for company in companies:
                    discovered.append(self._company_to_record(company, f"sector:{sector}", "sector_search"))
        else:
            console.print(f"[red]No results found[/red]")
        
        input("\nPress Enter to continue...")
    
    def _view_discovered(self, discovered: List[Dict]):
        """View discovered companies"""
        if not discovered:
            console.print("[yellow]No companies discovered yet[/yellow]")
            input("Press Enter to continue...")
            return
        
        df = pd.DataFrame(discovered)
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Ticker", width=10)
        table.add_column("CSIN", width=15)
        table.add_column("Name", width=35)
        table.add_column("Sector", width=20)
        table.add_column("Found Via", width=10)
        
        for _, row in df.iterrows():
            table.add_row(
                row['search_ticker'],
                row['csin'],
                row['company_name'][:35],
                row['sector'].split('/')[-1] if row['sector'] else 'N/A',
                row['found_via']
            )
        
        console.print(table)
        input("\nPress Enter to continue...")
    
    def _export_results(self, discovered: List[Dict]):
        """Export discovered companies"""
        if not discovered:
            console.print("[yellow]No companies to export[/yellow]")
            input("Press Enter to continue...")
            return
        
        df = pd.DataFrame(discovered)
        
        # Create simplified mapping for company_mappings.csv
        mapping_df = df[['search_ticker', 'csin', 'company_name', 'sector']].copy()
        mapping_df.rename(columns={'search_ticker': 'ticker'}, inplace=True)
        
        # Save files
        mapping_df.to_csv('config/company_mappings.csv', index=False)
        df.to_csv('config/company_discovery_full.csv', index=False)
        
        console.print(f"\n[green]Exported {len(df)} companies to:[/green]")
        console.print("  - config/company_mappings.csv (simplified)")
        console.print("  - config/company_discovery_full.csv (full details)")
        
        input("\nPress Enter to continue...")