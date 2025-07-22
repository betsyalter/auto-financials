import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.columns import Columns
import pandas as pd
from typing import List, Dict, Optional
import json
from pathlib import Path
from src.canalyst_client import CanalystClient
from loguru import logger
from src.utils.paths import resolve_path

console = Console()

class KPIDiscoveryTool:
    def __init__(self, client: CanalystClient):
        self.client = client
        self.selected_kpis = {}
        
    def discover_company_kpis(self, ticker: str, company_id: str) -> List[Dict]:
        """Discover all available KPIs for a company"""
        console.print(f"\n[bold blue]Discovering KPIs for {ticker} (Company ID: {company_id})...[/bold blue]")
        
        # Get latest model
        model = self.client.get_latest_equity_model(company_id)
        model_version = model['model_version']['name']
        
        console.print(f"Using model version: {model_version}")
        console.print(f"Most recent period: {model['most_recent_period']['name']}")
        
        # Get ALL time series (not just KPIs)
        all_time_series = self.client.list_time_series(
            company_id, 
            model_version,
            is_kpi=None  # Get ALL time series
        )
        
        console.print(f"\nFound [bold green]{len(all_time_series)} time series metrics[/bold green]")
        
        return all_time_series
    
    def display_kpis_by_category(self, time_series_list: List[Dict]):
        """Display KPIs organized by category"""
        # Group by category
        categories = {}
        for ts in time_series_list:
            category = ts['category']['description']
            if category not in categories:
                categories[category] = []
            categories[category].append(ts)
        
        # Display each category
        for category, kpis in sorted(categories.items()):
            console.print(f"\n[bold yellow]{category}[/bold yellow] ({len(kpis)} KPIs)")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Primary Name", width=30)
            table.add_column("Description", width=50)
            table.add_column("Unit", width=15)
            table.add_column("All Names", width=40)
            
            for kpi in sorted(kpis, key=lambda x: x['names'][0]):
                table.add_row(
                    kpi['names'][0],  # Primary name
                    kpi['description'],
                    kpi['unit']['description'],
                    ", ".join(kpi['names'][1:3]) if len(kpi['names']) > 1 else ""
                )
            
            console.print(table)
    
    def search_kpis(self, time_series_list: List[Dict], search_term: str) -> List[Dict]:
        """Search KPIs by name or description"""
        search_lower = search_term.lower()
        results = []
        
        for ts in time_series_list:
            # Search in names
            if any(search_lower in name.lower() for name in ts['names']):
                results.append(ts)
                continue
            
            # Search in description
            if search_lower in ts['description'].lower():
                results.append(ts)
                continue
            
            # Search in category
            if search_lower in ts['category']['description'].lower():
                results.append(ts)
        
        return results
    
    def interactive_selection(self, ticker: str, company_id: str, time_series_list: List[Dict]):
        """Interactive KPI selection interface"""
        selected = []
        
        while True:
            console.clear()
            console.print(Panel(f"[bold]KPI Selection for {ticker}[/bold]\n"
                              f"Selected: {len(selected)} KPIs", 
                              expand=False))
            
            options = [
                "1. View all KPIs by category",
                "2. Search KPIs by keyword",
                "3. View common/recommended KPIs",
                "4. Add KPI by exact name",
                "5. View selected KPIs",
                "6. Save and continue",
                "7. Cancel"
            ]
            
            for option in options:
                console.print(f"  {option}")
            
            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5", "6", "7"])
            
            if choice == "1":
                self._view_by_category_interactive(time_series_list, selected)
                
            elif choice == "2":
                self._search_interactive(time_series_list, selected)
                
            elif choice == "3":
                self._show_recommended_kpis(time_series_list, selected)
                
            elif choice == "4":
                self._add_by_name(time_series_list, selected)
                
            elif choice == "5":
                self._view_selected(selected)
                
            elif choice == "6":
                if selected:
                    self.selected_kpis[company_id] = selected
                    console.print(f"\n[bold green]Saved {len(selected)} KPIs for {ticker}[/bold green]")
                    break
                else:
                    console.print("[bold red]No KPIs selected![/bold red]")
                    
            elif choice == "7":
                if Confirm.ask("Cancel without saving?"):
                    break
    
    def _view_by_category_interactive(self, time_series_list: List[Dict], selected: List[Dict]):
        """Interactive category view with selection"""
        categories = {}
        for ts in time_series_list:
            category = ts['category']['description']
            if category not in categories:
                categories[category] = []
            categories[category].append(ts)
        
        # Show category list
        console.print("\n[bold]Categories:[/bold]")
        cat_list = sorted(categories.keys())
        for i, cat in enumerate(cat_list, 1):
            console.print(f"  {i}. {cat} ({len(categories[cat])} KPIs)")
        
        cat_choice = Prompt.ask("\nSelect category (or 'back')")
        
        if cat_choice.lower() == 'back':
            return
        
        try:
            selected_cat = cat_list[int(cat_choice) - 1]
            kpis = categories[selected_cat]
            
            # Show KPIs in category
            console.print(f"\n[bold]{selected_cat}[/bold]")
            for i, kpi in enumerate(kpis, 1):
                marker = "[green]✓[/green]" if any(k['slug'] == kpi['slug'] for k in selected) else " "
                console.print(f"{marker} {i}. {kpi['names'][0]}: {kpi['description']}")
            
            # Selection
            selections = Prompt.ask("\nSelect KPIs (comma-separated numbers, 'all', or 'back')")
            
            if selections.lower() == 'all':
                for kpi in kpis:
                    if not any(k['slug'] == kpi['slug'] for k in selected):
                        selected.append(kpi)
            elif selections.lower() != 'back':
                indices = [int(x.strip()) - 1 for x in selections.split(',')]
                for idx in indices:
                    if 0 <= idx < len(kpis):
                        kpi = kpis[idx]
                        if not any(k['slug'] == kpi['slug'] for k in selected):
                            selected.append(kpi)
                            
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
        
        input("\nPress Enter to continue...")
    
    def _search_interactive(self, time_series_list: List[Dict], selected: List[Dict]):
        """Interactive search for KPIs"""
        search_term = Prompt.ask("\nEnter search term (or 'back')")
        
        if search_term.lower() == 'back':
            return
        
        results = self.search_kpis(time_series_list, search_term)
        
        if not results:
            console.print("[red]No KPIs found matching your search[/red]")
        else:
            console.print(f"\n[bold]Found {len(results)} matching KPIs:[/bold]")
            for i, kpi in enumerate(results[:20], 1):  # Show max 20 results
                marker = "[green]✓[/green]" if any(k['slug'] == kpi['slug'] for k in selected) else " "
                console.print(f"{marker} {i}. {kpi['names'][0]}: {kpi['description']} ({kpi['category']['description']})")
            
            if len(results) > 20:
                console.print(f"\n[dim]... and {len(results) - 20} more results[/dim]")
            
            # Selection
            selections = Prompt.ask("\nSelect KPIs (comma-separated numbers, 'all', or 'back')")
            
            if selections.lower() == 'all':
                for kpi in results:
                    if not any(k['slug'] == kpi['slug'] for k in selected):
                        selected.append(kpi)
            elif selections.lower() != 'back':
                try:
                    indices = [int(x.strip()) - 1 for x in selections.split(',')]
                    for idx in indices:
                        if 0 <= idx < len(results):
                            kpi = results[idx]
                            if not any(k['slug'] == kpi['slug'] for k in selected):
                                selected.append(kpi)
                except ValueError:
                    console.print("[red]Invalid selection[/red]")
        
        input("\nPress Enter to continue...")
    
    def _show_recommended_kpis(self, time_series_list: List[Dict], selected: List[Dict]):
        """Show commonly used KPIs"""
        # Common financial KPIs (you can customize this list)
        common_patterns = {
            'Revenue': ['revenue', 'sales', 'turnover'],
            'Profitability': ['ebitda', 'ebit', 'net_income', 'earnings'],
            'Margins': ['margin', 'gross_profit', 'operating_profit'],
            'Per Share': ['eps', 'dps', 'per_share'],
            'Cash Flow': ['cash_flow', 'fcf', 'operating_cash'],
            'Balance Sheet': ['assets', 'liabilities', 'equity', 'debt'],
            'Valuation': ['pe_ratio', 'ev_ebitda', 'price_to_book'],
            'Growth': ['growth', 'yoy', 'cagr']
        }
        
        console.print("\n[bold]Recommended KPIs by Type:[/bold]")
        
        recommendations = {}
        for category, patterns in common_patterns.items():
            matches = []
            for ts in time_series_list:
                # Check if any pattern matches
                ts_text = f"{' '.join(ts['names'])} {ts['description']}".lower()
                if any(pattern in ts_text for pattern in patterns):
                    matches.append(ts)
            
            if matches:
                recommendations[category] = matches[:5]  # Top 5 per category
        
        # Display recommendations
        all_recommended = []
        for category, kpis in recommendations.items():
            console.print(f"\n[yellow]{category}:[/yellow]")
            for i, kpi in enumerate(kpis):
                all_recommended.append(kpi)
                idx = len(all_recommended)
                marker = "[green]✓[/green]" if any(k['slug'] == kpi['slug'] for k in selected) else " "
                console.print(f"{marker} {idx}. {kpi['names'][0]}: {kpi['description']}")
        
        # Allow selection
        selections = Prompt.ask("\nSelect KPIs (comma-separated numbers, 'all', or 'back')")
        
        if selections.lower() == 'all':
            for kpi in all_recommended:
                if not any(k['slug'] == kpi['slug'] for k in selected):
                    selected.append(kpi)
        elif selections.lower() != 'back':
            try:
                indices = [int(x.strip()) - 1 for x in selections.split(',')]
                for idx in indices:
                    if 0 <= idx < len(all_recommended):
                        kpi = all_recommended[idx]
                        if not any(k['slug'] == kpi['slug'] for k in selected):
                            selected.append(kpi)
            except ValueError:
                console.print("[red]Invalid selection[/red]")
        
        input("\nPress Enter to continue...")
    
    def _add_by_name(self, time_series_list: List[Dict], selected: List[Dict]):
        """Add KPI by exact name"""
        name = Prompt.ask("\nEnter exact KPI name (or 'back')")
        
        if name.lower() == 'back':
            return
        
        # Find exact match
        found = None
        for ts in time_series_list:
            if name in ts['names']:
                found = ts
                break
        
        if found:
            if not any(k['slug'] == found['slug'] for k in selected):
                selected.append(found)
                console.print(f"[green]Added: {found['names'][0]} - {found['description']}[/green]")
            else:
                console.print("[yellow]KPI already selected[/yellow]")
        else:
            console.print("[red]KPI not found. Make sure to use the exact name.[/red]")
        
        input("\nPress Enter to continue...")
    
    def _view_selected(self, selected: List[Dict]):
        """View currently selected KPIs"""
        if not selected:
            console.print("\n[yellow]No KPIs selected yet[/yellow]")
        else:
            console.print(f"\n[bold]Selected KPIs ({len(selected)}):[/bold]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", width=5)
            table.add_column("Name", width=30)
            table.add_column("Description", width=50)
            table.add_column("Category", width=25)
            
            for i, kpi in enumerate(selected, 1):
                table.add_row(
                    str(i),
                    kpi['names'][0],
                    kpi['description'],
                    kpi['category']['description']
                )
            
            console.print(table)
        
        input("\nPress Enter to continue...")
    
    def export_selections(self, output_path: Optional[str] = None):
        if output_path is None:
            # Try direct path first (for deployment), then resolve_path
            output_path = Path('config/kpi_mappings.csv')
            if not output_path.parent.exists():
                output_path = resolve_path('kpi_refresh_system', 'config', 'kpi_mappings.csv')
        else:
            output_path = Path(output_path)
        """Export selected KPIs to CSV"""
        rows = []
        
        for company_id, kpis in self.selected_kpis.items():
            for kpi in kpis:
                rows.append({
                    'company_id': company_id,
                    'time_series_name': kpi['names'][0],  # Primary name
                    'time_series_slug': kpi['slug'],
                    'kpi_label': kpi['description'],
                    'units': kpi['unit']['description'],
                    'category': kpi['category']['description'],
                    'all_names': '|'.join(kpi['names']),  # Pipe-separated
                    'priority': 1  # Default priority
                })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        console.print(f"\n[bold green]Exported {len(rows)} KPI selections to {output_path}[/bold green]")
        
        return df