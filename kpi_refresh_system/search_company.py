"""
Quick company search utility
Usage: python search_company.py "company name or ticker"
"""
import sys
from main import KPIRefreshApp
from csin_discovery import CSINDiscoveryTool

def search_company(search_term):
    """Search for a company by name or ticker"""
    app = KPIRefreshApp()
    discovery = CSINDiscoveryTool(app.client)
    
    print(f"\nSearching for '{search_term}'...\n")
    
    # Try searching by name first
    companies = discovery.search_by_name(search_term)
    if companies:
        print(f"Found by name:")
        for company in companies[:5]:
            print(f"  - {company['name']} (ID: {company['company_id']})")
            print(f"    Tickers: {company.get('tickers', {})}\n")
        return
    
    # Try different ticker types
    for ticker_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
        companies = discovery.search_by_ticker(search_term, ticker_type)
        if companies:
            print(f"Found via {ticker_type} ticker:")
            for company in companies[:3]:
                print(f"  - {company['name']} (ID: {company['company_id']})")
                print(f"    All tickers: {company.get('tickers', {})}\n")
            return
    
    print(f"No companies found for '{search_term}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        search_term = " ".join(sys.argv[1:])
        search_company(search_term)
    else:
        print("Usage: python search_company.py \"company name or ticker\"")
        print("Example: python search_company.py \"Shark Ninja\"")
        print("Example: python search_company.py SN")