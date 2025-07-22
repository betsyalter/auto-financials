"""
Select Tickers Page - Configure companies and metrics to analyze
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from csin_discovery import CSINDiscoveryTool
from src.services.kpi_service import KPIService
from main import KPIRefreshApp

st.set_page_config(
    page_title="Select Tickers - KPI Dashboard",
    page_icon="🏢",
    layout="wide"
)

# Initialize session state
if 'app' not in st.session_state:
    st.session_state.app = KPIRefreshApp()
    st.session_state.kpi_service = KPIService(
        st.session_state.app.client,
        st.session_state.app.processor,
        st.session_state.app.company_mappings
    )
    st.session_state.selected_ticker = None
    st.session_state.company_data = None
    st.session_state.selected_kpis = []
    st.session_state.fetched_data = None
    st.session_state.is_multi_company = False
    st.session_state.companies_data = {}
    st.session_state.metric_groups = []

st.title("🏢 Select Companies")
st.markdown("### Step 1: Search for Companies to Analyze")

# Instructions
with st.expander("📖 How to Use This Page", expanded=False):
    st.markdown("""
    ### Quick Start Guide
    
    **1️⃣ Search for Companies**
    - **Single Company**: Enter one ticker (e.g., `AAPL` or `MSFT`)
    - **Multiple Companies**: Enter comma-separated tickers (e.g., `AAPL, MSFT, GOOGL`)
    
    **2️⃣ After finding companies:**
    - Single company → Go to "By Company" page
    - Multiple companies → Go to "By Metric" page
    
    ### Tips
    - 🔍 If a ticker doesn't work, try searching by company name in the terminal
    - 🏢 Compare companies in the same industry for best results
    
    ### Common Issues
    - **"Company not found"**: Try different ticker format or use `python search_company.py "Company Name"`
    - **API errors**: Check your API key in the .env file
    """)

st.markdown("---")

# Company Search
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input(
            "Enter Company Tickers (comma-separated for comparison)", 
            placeholder="e.g., AAPL, MSFT, META",
            help="Enter multiple tickers separated by commas to compare companies"
        ).upper()
    
    with col2:
        st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
        search_button = st.button("🔍 Search Companies", type="primary", use_container_width=True)

# Search for company/companies
if search_button and ticker_input:
    # Parse tickers
    tickers = [t.strip() for t in ticker_input.split(',') if t.strip()]
    
    # Determine if multi-company mode
    st.session_state.is_multi_company = len(tickers) > 1
    
    if st.session_state.is_multi_company:
        # Multi-company search
        with st.spinner(f"Searching for {len(tickers)} companies..."):
            discovery = CSINDiscoveryTool(st.session_state.app.client)
            found_companies = {}
            not_found = []
            
            for ticker in tickers:
                companies = None
                for ticker_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
                    companies = discovery.search_by_ticker(ticker, ticker_type)
                    if companies:
                        break
                
                if companies:
                    found_companies[ticker] = companies[0]
                else:
                    not_found.append(ticker)
            
            if found_companies:
                st.session_state.companies_data = found_companies
                st.session_state.selected_ticker = ticker_input
                st.session_state.selected_kpis = []
                st.session_state.fetched_data = None
                
                # Show found companies
                st.success(f"✅ Found {len(found_companies)} companies:")
                for ticker, company in found_companies.items():
                    st.write(f"   • **{ticker}**: {company['name']}")
                
                if not_found:
                    st.warning(f"⚠️ Not found: {', '.join(not_found)}")
                
                # Next steps
                st.info("👉 Go to **'By Metric'** page to compare these companies")
            else:
                st.error("❌ No companies found")
                st.session_state.selected_ticker = None
                st.session_state.companies_data = {}
                st.session_state.selected_kpis = []
                st.session_state.fetched_data = None
    else:
        # Single company search
        with st.spinner(f"Searching for {ticker_input}..."):
            discovery = CSINDiscoveryTool(st.session_state.app.client)
            
            companies = None
            for ticker_type in ['canalyst', 'bloomberg', 'capiq', 'factset', 'thomson']:
                companies = discovery.search_by_ticker(ticker_input, ticker_type)
                if companies:
                    break
            
            if companies:
                company = companies[0]
                # Clear previous data when switching companies
                if st.session_state.selected_ticker != ticker_input:
                    st.session_state.selected_kpis = []
                    st.session_state.fetched_data = None
                    if 'available_metrics' in st.session_state:
                        del st.session_state.available_metrics
                    if 'model_version' in st.session_state:
                        del st.session_state.model_version
                    if 'metric_display_order' in st.session_state:
                        del st.session_state.metric_display_order
                
                st.session_state.selected_ticker = ticker_input
                st.session_state.company_data = company
                st.session_state.is_multi_company = False
                st.success(f"✅ Found: **{company['name']}**")
                
                # Show company info
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Company ID", company['company_id'])
                with col2:
                    st.metric("Ticker", ticker_input)
                
                # Next steps
                st.info("👉 Go to **'By Company'** page to analyze this company")
            else:
                st.error(f"❌ Company not found for ticker: {ticker_input}")
                st.session_state.selected_ticker = None
                st.session_state.company_data = None

# Display current state
st.markdown("---")
st.markdown("### Current Selection")

if st.session_state.is_multi_company and st.session_state.companies_data:
    st.success(f"✅ {len(st.session_state.companies_data)} companies selected for comparison")
    cols = st.columns(min(len(st.session_state.companies_data), 4))
    for i, (ticker, company) in enumerate(st.session_state.companies_data.items()):
        with cols[i % 4]:
            st.metric(ticker, company['name'][:30])
elif st.session_state.company_data:
    st.success("✅ Single company selected")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Company", st.session_state.company_data['name'])
    with col2:
        st.metric("Ticker", st.session_state.selected_ticker)
else:
    st.info("🔍 No companies selected yet. Use the search box above.")