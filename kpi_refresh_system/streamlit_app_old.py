import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime
import json
from io import BytesIO
import tenacity
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.canalyst_client import CanalystClient
from src.display_utils import (
    sort_period, format_value, check_needs_mm, add_mm_suffix,
    format_dataframe_for_display, create_period_columns
)
from src.utils.export_utils import to_excel_multi_sheets
from src.services.kpi_service import KPIService
from src.components.charts import (
    create_line_chart, create_bar_chart, 
    create_multi_company_comparison_chart,
    create_growth_comparison_chart
)
from src.components.tables import (
    prepare_display_dataframe, format_table_for_display,
    create_metric_selection_df, prepare_excel_export_data
)
from csin_discovery import CSINDiscoveryTool
from main import KPIRefreshApp

# Page config - Force rebuild
st.set_page_config(
    page_title="Financial Data Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

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
    st.session_state.companies_data = {}  # For multi-company mode
    st.session_state.metric_groups = []  # For multi-company metric groups

# Header
st.title("📊 Financial Data Explorer")

# Instructions
with st.expander("📖 How to Use This App", expanded=True):
    st.markdown("""
    ### Quick Start Guide
    
    **1️⃣ Search for Companies**
    - **Single Company**: Enter one ticker (e.g., `AAPL` or `MSFT`)
    - **Multiple Companies**: Enter comma-separated tickers (e.g., `AAPL, MSFT, GOOGL`)
    
    **2️⃣ Select Financial Metrics**
    - **Single Company Mode**: Choose from categories, search, or pick common KPIs
    - **Multi-Company Mode**: Create metric groups to compare similar metrics across companies
    
    **3️⃣ View Your Data**
    - **Data Table**: See all values with growth metrics
    - **Interactive Charts**: Visualize trends over time
    - **Download**: Export to Excel for further analysis
    
    ### Tips
    - 🔍 If a ticker doesn't work, try searching by company name in the terminal
    - 📊 Use ", mm" suffix to show values in millions
    - 📈 Toggle QoQ and YoY growth metrics on/off in table display
    - 🏢 Compare companies in the same industry for best results
    
    ### Common Issues
    - **"Company not found"**: Try different ticker format or use `python search_company.py "Company Name"`
    - **Missing data**: Some companies may not have all metrics available
    - **API errors**: Check your API key in the .env file
    """)
    
    # Add a button to collapse instructions after reading
    if st.button("Got it! Hide instructions"):
        st.rerun()

st.markdown("---")

# Step 1: Company Search
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input("Enter Company Tickers (comma-separated for comparison)", 
                                     placeholder="e.g., AAPL, MSFT, META",
                                     help="Enter multiple tickers separated by commas to compare companies").upper()
    
    with col2:
        # Add invisible label to match text input's label height
        st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
        search_button = st.button("🔍 Search Companies", type="primary", use_container_width=True)

# Search for company/companies
if search_button and ticker_input:
    # Parse tickers - could be single or multiple
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
                    st.write(f"   • {ticker}: {company['name']}")
                
                if not_found:
                    st.warning(f"⚠️ Not found: {', '.join(not_found)}")
            else:
                st.error("❌ No companies found")
                st.session_state.selected_ticker = None
                st.session_state.companies_data = {}
                st.session_state.selected_kpis = []
                st.session_state.fetched_data = None
    else:
        # Single company search (existing logic)
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
                st.success(f"✅ Found: {company['name']}")
            else:
                st.error(f"❌ Company not found for ticker: {ticker_input}")
                st.session_state.selected_ticker = None
                st.session_state.company_data = None
                st.session_state.selected_kpis = []
                st.session_state.fetched_data = None

# Step 2: Display company info and KPI selection
if (hasattr(st.session_state, 'company_data') and st.session_state.company_data) or (hasattr(st.session_state, 'companies_data') and st.session_state.companies_data):
    # Company info card
    st.markdown("### Company Information")
    
    if st.session_state.is_multi_company:
        # Multi-company display
        companies = st.session_state.companies_data
        cols = st.columns(min(len(companies), 3))
        for i, (ticker, company) in enumerate(companies.items()):
            with cols[i % 3]:
                st.metric("Company", f"{ticker}: {company['name']}")
                st.caption(company.get('sector', {}).get('path', 'N/A').split(':')[-1])
    else:
        # Single company display
        company = st.session_state.company_data
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Company Name", company['name'])
        with col2:
            st.metric("Ticker", st.session_state.selected_ticker)
        with col3:
            st.metric("Sector", company.get('sector', {}).get('path', 'N/A').split(':')[-1])
    
    # KPI Discovery
    st.markdown("### Select Financial Metrics")
    
    if st.session_state.is_multi_company:
        # Multi-company metric discovery
        st.info("Discover and select metrics for each company individually, then create metric groups for comparison.")
        
        # Initialize storage for selected metrics per company
        if 'selected_metrics_per_company' not in st.session_state:
            st.session_state.selected_metrics_per_company = {}
        
        # Create tabs for each company
        company_tabs = st.tabs([ticker for ticker in st.session_state.companies_data.keys()])
        
        for tab_idx, (ticker, company) in enumerate(st.session_state.companies_data.items()):
            with company_tabs[tab_idx]:
                st.markdown(f"#### {ticker}: {company['name']}")
                
                # Initialize selected metrics for this company
                if ticker not in st.session_state.selected_metrics_per_company:
                    st.session_state.selected_metrics_per_company[ticker] = []
                
                # Discover metrics button for this company
                if st.button(f"🔄 Discover Available Metrics for {ticker}", key=f"discover_{ticker}"):
                    with st.spinner(f"Fetching metrics for {ticker}..."):
                        try:
                            # Get latest model
                            model = st.session_state.app.client.get_latest_equity_model(company['company_id'])
                            model_version = model['model_version']['name']
                            
                            # Get all time series
                            time_series = st.session_state.app.client.list_time_series(
                                company['company_id'],
                                model_version,
                                is_kpi=None
                            )
                            
                            # Store in session state
                            if 'all_companies_metrics' not in st.session_state:
                                st.session_state.all_companies_metrics = {}
                            if 'model_versions' not in st.session_state:
                                st.session_state.model_versions = {}
                            
                            st.session_state.all_companies_metrics[ticker] = time_series
                            st.session_state.model_versions[ticker] = model_version
                            
                            st.success(f"Found {len(time_series)} metrics for {ticker}!")
                            
                        except Exception as e:
                            st.error(f"Error fetching metrics for {ticker}: {str(e)}")
                
                # Show metric selection interface if metrics are available
                if 'all_companies_metrics' in st.session_state and ticker in st.session_state.all_companies_metrics:
                    metrics = st.session_state.all_companies_metrics[ticker]
                    
                    # Metric selection tabs (similar to single company)
                    metric_tabs = st.tabs(["📂 By Category", "🔍 Search", "⭐ Common KPIs"])
                    
                    with metric_tabs[0]:  # By Category
                        # Group by category
                        categories = {}
                        for ts in metrics:
                            cat = ts['category']['description']
                            if cat not in categories:
                                categories[cat] = []
                            categories[cat].append(ts)
                        
                        selected_category = st.selectbox(f"Select Category", sorted(categories.keys()), 
                                                       key=f"cat_select_{ticker}")
                        
                        if selected_category:
                            st.write(f"**{len(categories[selected_category])} metrics in {selected_category}:**")
                            
                            for ts in categories[selected_category][:20]:
                                checkbox_key = f"{ticker}_cat_{ts['slug']}"
                                is_selected = ts in st.session_state.selected_metrics_per_company[ticker]
                                
                                if st.checkbox(f"{ts['description']} ({ts['unit']['description']})", 
                                             value=is_selected,
                                             key=checkbox_key):
                                    if ts not in st.session_state.selected_metrics_per_company[ticker]:
                                        st.session_state.selected_metrics_per_company[ticker].append(ts)
                                else:
                                    if ts in st.session_state.selected_metrics_per_company[ticker]:
                                        st.session_state.selected_metrics_per_company[ticker].remove(ts)
                    
                    with metric_tabs[1]:  # Search
                        search_term = st.text_input(f"Search metrics", key=f"search_{ticker}")
                        
                        if search_term:
                            matching = [ts for ts in metrics
                                      if search_term.lower() in ts['description'].lower() or
                                      any(search_term.lower() in name.lower() for name in ts['names'])]
                            
                            st.write(f"**Found {len(matching)} matching metrics:**")
                            
                            for ts in matching[:20]:
                                checkbox_key = f"{ticker}_search_{ts['slug']}"
                                is_selected = ts in st.session_state.selected_metrics_per_company[ticker]
                                
                                if st.checkbox(f"{ts['description']} ({ts['unit']['description']})", 
                                             value=is_selected,
                                             key=checkbox_key):
                                    if ts not in st.session_state.selected_metrics_per_company[ticker]:
                                        st.session_state.selected_metrics_per_company[ticker].append(ts)
                                else:
                                    if ts in st.session_state.selected_metrics_per_company[ticker]:
                                        st.session_state.selected_metrics_per_company[ticker].remove(ts)
                    
                    with metric_tabs[2]:  # Common KPIs
                        common_keywords = [
                            ('Total Revenue', 'total revenue'),
                            ('Gross Profit', 'gross profit'),
                            ('Operating Income', 'operating income'),
                            ('Net Income', 'net income'),
                            ('EPS', 'eps'),
                            ('Free Cash Flow', 'free cash flow')
                        ]
                        
                        for display_name, keyword in common_keywords:
                            matching = [ts for ts in metrics 
                                      if keyword in ts['description'].lower()]
                            if matching:
                                ts = matching[0]
                                checkbox_key = f"{ticker}_common_{keyword.replace(' ', '_')}"
                                is_selected = ts in st.session_state.selected_metrics_per_company[ticker]
                                
                                if st.checkbox(f"{display_name}: {ts['description']} ({ts['unit']['description']})", 
                                             value=is_selected,
                                             key=checkbox_key):
                                    if ts not in st.session_state.selected_metrics_per_company[ticker]:
                                        st.session_state.selected_metrics_per_company[ticker].append(ts)
                                else:
                                    if ts in st.session_state.selected_metrics_per_company[ticker]:
                                        st.session_state.selected_metrics_per_company[ticker].remove(ts)
                    
                    # Show selected metrics count
                    selected_count = len(st.session_state.selected_metrics_per_company[ticker])
                    if selected_count > 0:
                        st.info(f"Selected {selected_count} metrics for {ticker}")
                        
                        if st.button(f"Clear Selection for {ticker}", key=f"clear_{ticker}"):
                            st.session_state.selected_metrics_per_company[ticker] = []
                            st.rerun()
    
    else:
        # Single company mode
        if st.button("🔄 Discover Available Metrics"):
            with st.spinner("Fetching available metrics..."):
                try:
                    # Clear previous selections when rediscovering metrics
                    st.session_state.selected_kpis = []
                    st.session_state.fetched_data = None
                    if 'metric_display_order' in st.session_state:
                        del st.session_state.metric_display_order
                    
                    company = st.session_state.company_data
                    model = st.session_state.app.client.get_latest_equity_model(company['company_id'])
                    model_version = model['model_version']['name']
                    
                    all_time_series = st.session_state.app.client.list_time_series(
                        company['company_id'],
                        model_version,
                        is_kpi=None
                    )
                    
                    st.session_state.available_metrics = all_time_series
                    st.session_state.model_version = model_version
                    st.success(f"Found {len(all_time_series)} available metrics!")
                    
                except Exception as e:
                    st.error(f"Error fetching metrics: {str(e)}")
    
    # Show metric groups section only after metrics are selected
    if (st.session_state.is_multi_company and 
        'selected_metrics_per_company' in st.session_state and
        any(len(metrics) > 0 for metrics in st.session_state.selected_metrics_per_company.values())):
        
        st.markdown("---")
        st.markdown("### Create Metric Groups for Comparison")
        st.info("Group similar metrics from different companies to create comparison tables.")
        
        # Show existing metric groups
        if st.session_state.metric_groups:
            st.markdown("#### Existing Metric Groups")
            for i, group in enumerate(st.session_state.metric_groups):
                with st.expander(f"📊 {group['name']}", expanded=False):
                    for ticker, metric_info in group['metrics'].items():
                        if metric_info:
                            if isinstance(metric_info, list):
                                # Multiple metrics selected - show combined
                                descriptions = [m['description'] for m in metric_info]
                                combined_desc = " + ".join(descriptions)
                                st.write(f"**{ticker}**: {combined_desc}")
                            else:
                                # Single metric (legacy support)
                                st.write(f"**{ticker}**: {metric_info['description']} ({metric_info['unit']})")
                        else:
                            st.write(f"**{ticker}**: *Not selected*")
                    
                    if st.button(f"Delete Group", key=f"delete_group_{i}"):
                        st.session_state.metric_groups.pop(i)
                        st.rerun()
        
        # Create new metric group
        st.markdown("#### Create New Metric Group")
        with st.expander("➕ Add Metric Group", expanded=True):
            group_name = st.text_input("Group Name (e.g., 'Revenue', 'Profit', 'Margins')")
            
            if group_name:
                st.markdown("**Select corresponding metric from each company:**")
                
                new_group_metrics = {}
                
                # Create columns for each company
                cols = st.columns(len(st.session_state.companies_data))
                
                for col_idx, (ticker, company) in enumerate(st.session_state.companies_data.items()):
                    with cols[col_idx]:
                        st.markdown(f"**{ticker}**")
                        
                        # Get only the pre-selected metrics for this company
                        selected_metrics = st.session_state.selected_metrics_per_company.get(ticker, [])
                        
                        if selected_metrics:
                            # Allow multiple metric selection with checkboxes
                            selected_for_group = []
                            
                            for m in selected_metrics:
                                if st.checkbox(f"{m['description']} ({m['unit']['description']})", 
                                             key=f"group_{ticker}_{group_name}_{m['slug']}"):
                                    selected_for_group.append({
                                        'description': m['description'],
                                        'unit': m['unit']['description'],
                                        'names': m['names'],
                                        'slug': m['slug'],
                                        'category': m['category']['description']
                                    })
                            
                            if selected_for_group:
                                new_group_metrics[ticker] = selected_for_group
                            else:
                                new_group_metrics[ticker] = None
                        else:
                            st.warning(f"No metrics selected for {ticker}")
                            new_group_metrics[ticker] = None
                
                # Add group button
                if st.button("Create Metric Group", type="primary"):
                    if any(new_group_metrics.values()):  # At least one metric selected
                        st.session_state.metric_groups.append({
                            'name': group_name,
                            'metrics': new_group_metrics
                        })
                        st.success(f"Created metric group: {group_name}")
                        st.rerun()
                    else:
                        st.error("Please select at least one metric")
        
        # Show selected KPIs summary
        if st.session_state.metric_groups:
            st.markdown("### Selected Metrics Summary")
            total_metrics = sum(len([m for m in group['metrics'].values() if m]) 
                              for group in st.session_state.metric_groups)
            st.info(f"You have {len(st.session_state.metric_groups)} metric groups with {total_metrics} total metric selections")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear All Groups"):
                    st.session_state.metric_groups = []
                    st.rerun()
            
            with col2:
                if st.button("📊 Fetch Data", type="primary"):
                    with st.spinner("Fetching financial data..."):
                        try:
                            # Multi-company data fetching using metric groups
                            all_company_data = {}
                            
                            for ticker, company in st.session_state.companies_data.items():
                                company_id = company['company_id']
                                model_version = st.session_state.model_versions[ticker]
                                
                                # Collect all metrics for this company from all groups
                                temp_kpis = []
                                priority = 1
                                
                                for group in st.session_state.metric_groups:
                                    if ticker in group['metrics'] and group['metrics'][ticker]:
                                        metric_info = group['metrics'][ticker]
                                        
                                        if isinstance(metric_info, list):
                                            # Multiple metrics in this group - add each
                                            for m in metric_info:
                                                temp_kpis.append({
                                                    'company_id': company_id,
                                                    'time_series_name': m['names'][0],
                                                    'time_series_slug': m['slug'],
                                                    'kpi_label': m['description'],
                                                    'units': m['unit'],
                                                    'category': m['category'],
                                                    'all_names': ','.join(m['names']),
                                                    'priority': priority,
                                                    'group_name': group['name']  # Track which group this belongs to
                                                })
                                                priority += 1
                                        else:
                                            # Single metric (legacy support)
                                            temp_kpis.append({
                                                'company_id': company_id,
                                                'time_series_name': metric_info['names'][0],
                                                'time_series_slug': metric_info['slug'],
                                                'kpi_label': metric_info['description'],
                                                'units': metric_info['unit'],
                                                'category': metric_info['category'],
                                                'all_names': ','.join(metric_info['names']),
                                                'priority': priority,
                                                'group_name': group['name']
                                            })
                                            priority += 1
                                
                                if temp_kpis:
                                    temp_kpi_df = pd.DataFrame(temp_kpis)
                                    
                                    # Fetch data for this company
                                    historical_data = []
                                    for _, kpi in temp_kpi_df.iterrows():
                                        hist = st.session_state.app.client.get_historical_data_points(
                                            company_id,
                                            model_version,
                                            kpi['time_series_name']
                                        )
                                        historical_data.extend(hist)
                                    
                                    # Get periods
                                    hist_periods_data = st.session_state.app.client.get_historical_periods(
                                        company_id, 
                                        model_version
                                    )
                                    
                                    # Process data
                                    api_data = {
                                        'historical_data': historical_data,
                                        'forecast_data': [],
                                        'periods': hist_periods_data,
                                        'time_series_info': temp_kpi_df.to_dict('records')
                                    }
                                    
                                    df = st.session_state.app.processor.process_company_data(
                                        company_id, 
                                        api_data,
                                        temp_kpi_df
                                    )
                                    
                                    all_company_data[ticker] = df
                            
                            st.session_state.fetched_data = all_company_data
                            st.session_state.metric_groups_used = st.session_state.metric_groups.copy()
                            st.success(f"Data fetched successfully for {len(all_company_data)} companies!")
                            
                        except Exception as e:
                            if isinstance(e, (tenacity.RetryError, requests.ConnectionError)):
                                st.error(f"Connection problem fetching data.")
                                if st.button("🔁 Retry", key="retry_multi_fetch"):
                                    st.rerun()
                            else:
                                st.error(f"Error fetching data: {str(e)}")
    
    elif 'available_metrics' in st.session_state:
        # Single company mode (existing interface)
        tab1, tab2, tab3, tab4 = st.tabs(["📂 By Category", "🔍 Search", "⭐ Common KPIs", "📝 Manual Entry"])
        
        with tab1:
            # Group by category
            categories = {}
            for ts in st.session_state.available_metrics:
                cat = ts['category']['description']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(ts)
            
            selected_category = st.selectbox("Select Category", sorted(categories.keys()))
            
            if selected_category:
                st.write(f"**{len(categories[selected_category])} metrics in {selected_category}:**")
                
                # Display metrics in this category
                for ts in categories[selected_category][:20]:  # Show first 20
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        checkbox_key = f"cat_{ts['slug']}"
                        is_selected = ts in st.session_state.selected_kpis
                        if st.checkbox(f"{ts['description']} ({ts['unit']['description']})", 
                                     value=is_selected,
                                     key=checkbox_key):
                            if ts not in st.session_state.selected_kpis:
                                st.session_state.selected_kpis.append(ts)
                        else:
                            if ts in st.session_state.selected_kpis:
                                st.session_state.selected_kpis.remove(ts)
                        
        with tab2:
            search_term = st.text_input("Search for metrics (e.g., revenue, profit, margin)")
            
            if search_term:
                matching = [ts for ts in st.session_state.available_metrics 
                          if search_term.lower() in ts['description'].lower() or
                          any(search_term.lower() in name.lower() for name in ts['names'])]
                
                st.write(f"**Found {len(matching)} matching metrics:**")
                
                for ts in matching[:20]:  # Show first 20 results
                    checkbox_key = f"search_{ts['slug']}"
                    is_selected = ts in st.session_state.selected_kpis
                    if st.checkbox(f"{ts['description']} ({ts['unit']['description']})", 
                                 value=is_selected,
                                 key=checkbox_key):
                        if ts not in st.session_state.selected_kpis:
                            st.session_state.selected_kpis.append(ts)
                    else:
                        if ts in st.session_state.selected_kpis:
                            st.session_state.selected_kpis.remove(ts)
        
        with tab3:
            st.write("**Commonly selected financial metrics:**")
            
            common_keywords = [
                ('Total Revenue', 'total revenue'),
                ('Gross Profit', 'gross profit'),
                ('Operating Income', 'operating income'),
                ('Net Income', 'net income'),
                ('EPS', 'eps'),
                ('Free Cash Flow', 'free cash flow'),
                ('Total Assets', 'total assets'),
                ('Total Liabilities', 'total liabilities'),
                ('Gross Margin %', 'gross margin'),
                ('Operating Margin %', 'operating margin'),
                ('Net Margin %', 'net margin'),
                ('ROE %', 'return on equity')
            ]
            
            for display_name, keyword in common_keywords:
                matching = [ts for ts in st.session_state.available_metrics 
                          if keyword in ts['description'].lower()]
                if matching:
                    ts = matching[0]
                    checkbox_key = f"common_{keyword}"
                    is_selected = ts in st.session_state.selected_kpis
                    if st.checkbox(f"{display_name}: {ts['description']} ({ts['unit']['description']})", 
                                 value=is_selected,
                                 key=checkbox_key):
                        if ts not in st.session_state.selected_kpis:
                            st.session_state.selected_kpis.append(ts)
                    else:
                        if ts in st.session_state.selected_kpis:
                            st.session_state.selected_kpis.remove(ts)
        
        with tab4:
            exact_name = st.text_input("Enter exact metric name (e.g., z_Y8S4N80139_MO_OS_totalrevenue)")
            
            if exact_name and st.button("Add Metric"):
                matching = [ts for ts in st.session_state.available_metrics 
                          if exact_name in ts['names']]
                if matching:
                    ts = matching[0]
                    if ts not in st.session_state.selected_kpis:
                        st.session_state.selected_kpis.append(ts)
                        st.success(f"Added: {ts['description']}")
                else:
                    st.error("Metric not found")
        
        # Show selected KPIs
        if st.session_state.selected_kpis:
            st.markdown("### Selected Metrics")
            
            selected_df = pd.DataFrame([
                {
                    'Description': kpi['description'],
                    'Category': kpi['category']['description'],
                    'Units': kpi['unit']['description']
                }
                for kpi in st.session_state.selected_kpis
            ])
            
            st.dataframe(selected_df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Selection"):
                    st.session_state.selected_kpis = []
                    st.rerun()
            
            with col2:
                if st.button("📊 Fetch Data", type="primary"):
                    with st.spinner("Fetching financial data..."):
                        try:
                            if st.session_state.is_multi_company:
                                # Multi-company data fetching - use KPIService
                                all_company_data = st.session_state.kpi_service.fetch_multi_company_data(
                                    st.session_state.companies_data,
                                    st.session_state.selected_kpis,
                                    st.session_state.model_versions,
                                    st.session_state.all_companies_metrics
                                )
                                
                                st.session_state.fetched_data = all_company_data
                                st.success(f"Data fetched successfully for {len(all_company_data)} companies!")
                                
                            else:
                                # Single company mode - use KPIService
                                company = st.session_state.company_data
                                company_id = company['company_id']
                                
                                # Prepare KPI mappings using service
                                temp_kpi_df = st.session_state.kpi_service.prepare_single_company_kpis(
                                    company_id, 
                                    st.session_state.selected_kpis
                                )
                                
                                # Fetch data using service
                                df = st.session_state.kpi_service.fetch_kpi_data(
                                    company_id,
                                    temp_kpi_df,
                                    st.session_state.model_version
                                )
                                
                                # Check for KPIs with mostly missing values
                                warnings = []
                                for idx in df.index:
                                    if len(idx) == 4 and pd.isna(idx[3]):  # Base rows only
                                        row_data = df.loc[idx]
                                        non_null_count = row_data.notna().sum()
                                        total_count = len(row_data)
                                        
                                        if total_count > 0 and non_null_count / total_count < 0.3:  # Less than 30% data
                                            warnings.append({
                                                'kpi': idx[1],
                                                'available': non_null_count,
                                                'total': total_count
                                            })
                                
                                # Show warnings if any
                                if warnings:
                                    st.warning("⚠️ Some KPIs have limited data:")
                                    for w in warnings:
                                        st.write(f"- **{w['kpi']}**: Only {w['available']} of {w['total']} periods have data")
                                    
                                    if not st.checkbox("Include KPIs with limited data", value=True):
                                        # Filter out KPIs with limited data
                                        indices_to_remove = []
                                        for w in warnings:
                                            for idx in df.index:
                                                if len(idx) >= 2 and idx[1] == w['kpi']:
                                                    indices_to_remove.append(idx)
                                        df = df.drop(indices_to_remove)
                                
                                st.session_state.fetched_data = df
                                st.session_state.temp_kpi_df = temp_kpi_df
                                st.success("Data fetched successfully!")
                            
                        except Exception as e:
                            if isinstance(e, (tenacity.RetryError, requests.ConnectionError)):
                                st.error(f"Connection problem fetching data.")
                                if st.button("🔁 Retry", key="retry_single_fetch"):
                                    st.rerun()
                            else:
                                st.error(f"Error fetching data: {str(e)}")

# Step 3: Display and Export Data
if st.session_state.fetched_data is not None:
    st.markdown("### Financial Data")
    
    if st.session_state.is_multi_company:
        # Multi-company mode
        all_company_data = st.session_state.fetched_data
        
        # Add view mode toggle
        view_mode = st.radio("View Mode", ["By Metric", "By Company"], horizontal=True)
        
        # Display options
        display_tab1, display_tab2, display_tab3 = st.tabs(["📋 Data Table", "📊 Interactive Charts", "💾 Download"])
        
        with display_tab1:
            # Table customization options
            with st.expander("⚙️ Customize Table Display"):
                st.write("**Growth metrics display:**")
                col1, col2 = st.columns(2)
                with col1:
                    show_qoq = st.checkbox("Show Quarter-over-Quarter growth", value=True, key="multi_qoq")
                with col2:
                    show_yoy = st.checkbox("Show Year-over-Year growth", value=True, key="multi_yoy")
            
            if view_mode == "By Metric":
                # Create comparison table by metric group
                st.markdown("#### Comparison by Metric")
                
                # Use metric groups to create comparison tables
                if 'metric_groups_used' in st.session_state:
                    for group in st.session_state.metric_groups_used:
                        # Create comparison dataframe for this metric group
                        comparison_data = []
                        
                        # Check if we need mm suffix for this group
                        needs_mm = False
                        for ticker, metric_info in group['metrics'].items():
                            if metric_info and ticker in all_company_data:
                                df = all_company_data[ticker]
                                
                                # Handle both list and single metric
                                metrics_to_check = metric_info if isinstance(metric_info, list) else [metric_info]
                                
                                for m in metrics_to_check:
                                    # Find this metric in the data
                                    for idx in df.index:
                                        if len(idx) >= 2 and idx[1] == m['description'] and len(idx) == 4 and pd.isna(idx[3]):
                                            row_values = df.loc[idx]
                                            if any(abs(val) >= 1000000 for val in row_values if pd.notna(val)):
                                                needs_mm = True
                                                break
                                    if needs_mm:
                                        break
                        
                        # Create the comparison rows
                        for ticker, metric_info in group['metrics'].items():
                            if metric_info and ticker in all_company_data:
                                df = all_company_data[ticker]
                                
                                if isinstance(metric_info, list):
                                    # Multiple metrics - need to sum them
                                    # First collect base values
                                    base_values = {}
                                    qoq_values = {}
                                    yoy_values = {}
                                    
                                    for m in metric_info:
                                        for idx in df.index:
                                            if len(idx) >= 2 and idx[1] == m['description']:
                                                if len(idx) == 4 and pd.isna(idx[3]):
                                                    # Base metric - add to sum
                                                    for period in df.columns:
                                                        if period not in base_values:
                                                            base_values[period] = 0
                                                        val = df.loc[idx, period]
                                                        if pd.notna(val):
                                                            base_values[period] += val
                                                        else:
                                                            base_values[period] = None if base_values[period] == 0 else base_values[period]
                                                elif len(idx) == 4 and pd.notna(idx[3]):
                                                    # Growth metrics - collect them separately
                                                    if idx[3] == 'qoq growth':
                                                        for period in df.columns:
                                                            if period not in qoq_values:
                                                                qoq_values[period] = []
                                                            val = df.loc[idx, period]
                                                            if pd.notna(val):
                                                                qoq_values[period].append(val)
                                                    elif idx[3] == 'yoy growth':
                                                        for period in df.columns:
                                                            if period not in yoy_values:
                                                                yoy_values[period] = []
                                                            val = df.loc[idx, period]
                                                            if pd.notna(val):
                                                                yoy_values[period].append(val)
                                    
                                    # Add combined base row
                                    if base_values:
                                        row_data = {'Company': ticker, 'Type': ''}
                                        row_data.update(base_values)
                                        comparison_data.append(row_data)
                                    
                                    # Add growth rows if enabled
                                    if show_qoq and qoq_values:
                                        qoq_row = {'Company': ticker, 'Type': 'qoq growth'}
                                        for period, values in qoq_values.items():
                                            if values:
                                                # Average the growth rates
                                                qoq_row[period] = sum(values) / len(values)
                                            else:
                                                qoq_row[period] = None
                                        comparison_data.append(qoq_row)
                                    
                                    if show_yoy and yoy_values:
                                        yoy_row = {'Company': ticker, 'Type': 'yoy growth'}
                                        for period, values in yoy_values.items():
                                            if values:
                                                # Average the growth rates
                                                yoy_row[period] = sum(values) / len(values)
                                            else:
                                                yoy_row[period] = None
                                        comparison_data.append(yoy_row)
                                
                                else:
                                    # Single metric (legacy)
                                    for idx in df.index:
                                        if len(idx) >= 2 and idx[1] == metric_info['description']:
                                            if len(idx) == 4 and pd.isna(idx[3]):
                                                row_data = {'Company': ticker, 'Type': ''}
                                            elif len(idx) == 4 and pd.notna(idx[3]):
                                                # Check if we should include this growth metric
                                                if (idx[3] == 'qoq growth' and not show_qoq) or \
                                                   (idx[3] == 'yoy growth' and not show_yoy):
                                                    continue
                                                row_data = {'Company': ticker, 'Type': idx[3]}
                                            else:
                                                continue
                                            
                                            for period in df.columns:
                                                row_data[period] = df.loc[idx, period]
                                            
                                            comparison_data.append(row_data)
                        
                        if comparison_data:
                            comp_df = pd.DataFrame(comparison_data)
                            comp_df = comp_df.set_index(['Company', 'Type'])
                            
                            # Format the display using utility function
                            formatted_df = format_dataframe_for_display(
                                comp_df, 
                                include_growth={'qoq': show_qoq, 'yoy': show_yoy}
                            )
                            
                            # Add units to group name if needed
                            display_name = group['name']
                            if needs_mm and ", mm" not in display_name:
                                display_name = f"{display_name}, mm"
                            
                            st.markdown(f"**{display_name}**")
                            
                            # Guarantee uniqueness - only reset if not unique
                            if not formatted_df.index.is_unique:
                                formatted_df = formatted_df.reset_index(drop=True)
                            if not formatted_df.columns.is_unique:
                                formatted_df.columns = pd.io.parsers.ParserBase({'names':formatted_df.columns})._maybe_dedup_names(formatted_df.columns)
                            
                            # Display without styling
                            st.dataframe(
                                formatted_df,
                                use_container_width=True,
                                column_config={c: st.column_config.NumberColumn(format="%.2f") for c in formatted_df.select_dtypes('number').columns}
                            )
                            st.markdown("---")
                
            else:  # By Company view
                st.markdown("#### Comparison by Company")
                
                for ticker, df in all_company_data.items():
                    company_name = st.session_state.companies_data[ticker]['name']
                    st.markdown(f"**{ticker}: {company_name}**")
                    
                    # Display this company's data (similar to single company mode)
                    # Check which rows need ", mm" suffix
                    needs_mm = {}
                    for idx in df.index:
                        if len(idx) == 4 and pd.isna(idx[3]):  # Base row only
                            row_values = df.loc[idx]
                            needs_mm[idx] = any(abs(val) >= 1000000 for val in row_values if pd.notna(val))
                    
                    # Filter based on growth metrics checkboxes
                    indices_to_keep = []
                    for idx in df.index:
                        if len(idx) == 4 and pd.isna(idx[3]):
                            indices_to_keep.append(idx)  # Always keep base metrics
                        elif len(idx) == 4 and pd.notna(idx[3]):
                            if (idx[3] == 'qoq growth' and show_qoq) or \
                               (idx[3] == 'yoy growth' and show_yoy):
                                indices_to_keep.append(idx)
                    
                    display_df = df.loc[indices_to_keep].copy()
                    
                    # Create a copy and modify the multiindex to add mm suffix
                    new_multiindex = []
                    for idx in display_df.index:
                        if len(idx) == 4:
                            # Create a new tuple with modified description
                            if pd.isna(idx[3]) and needs_mm.get(idx, False) and ", mm" not in idx[1]:
                                new_idx = (idx[0], f"{idx[1]}, mm", idx[2], idx[3])
                            elif pd.notna(idx[3]):
                                # For growth rows, check if base needs mm
                                base_idx = idx[:-1] + (pd.NA,)
                                if needs_mm.get(base_idx, False) and ", mm" not in idx[1]:
                                    new_idx = (idx[0], f"{idx[1]}, mm", idx[2], idx[3])
                                else:
                                    new_idx = idx
                            else:
                                new_idx = idx
                            new_multiindex.append(new_idx)
                        else:
                            new_multiindex.append(idx)
                    
                    display_df.index = pd.MultiIndex.from_tuples(new_multiindex)
                    
                    # Format values using utility function
                    formatted_df = format_dataframe_for_display(
                        display_df,
                        include_growth={'qoq': show_qoq, 'yoy': show_yoy}
                    )
                    
                    # Create simple index for display
                    new_index = []
                    for idx in formatted_df.index:
                        if len(idx) == 4 and pd.isna(idx[3]):
                            new_index.append(idx[1])
                        elif len(idx) == 4 and pd.notna(idx[3]):
                            new_index.append(f"{idx[1]} - {idx[3]}")
                    
                    formatted_df.index = new_index
                    
                    # Guarantee uniqueness - only reset if not unique
                    if not formatted_df.index.is_unique:
                        formatted_df = formatted_df.reset_index(drop=True)
                    if not formatted_df.columns.is_unique:
                        formatted_df.columns = pd.io.parsers.ParserBase({'names':formatted_df.columns})._maybe_dedup_names(formatted_df.columns)
                    
                    # Display without styling
                    st.dataframe(
                        formatted_df,
                        use_container_width=True,
                        column_config={c: st.column_config.NumberColumn(format="%.2f") for c in formatted_df.select_dtypes('number').columns}
                    )
                    st.markdown("---")
        
        with display_tab2:
            # Multi-company interactive charts
            st.markdown("#### Interactive Charts")
            
            if 'metric_groups_used' in st.session_state and st.session_state.metric_groups_used:
                # Select metric group to visualize
                group_names = [g['name'] for g in st.session_state.metric_groups_used]
                selected_group_name = st.selectbox("Select Metric Group", group_names)
                
                # Find the selected group
                selected_group = next(g for g in st.session_state.metric_groups_used if g['name'] == selected_group_name)
                
                # Period type selection
                col1, col2 = st.columns([1, 3])
                with col1:
                    period_type = st.radio("Period Type", ["Annual", "Quarterly"])
                
                # Prepare data for all companies in this group
                chart_data = []
                
                for ticker, metric_info in selected_group['metrics'].items():
                    if metric_info and ticker in all_company_data:
                        df = all_company_data[ticker]
                        
                        if isinstance(metric_info, list):
                            # Multiple metrics - sum them
                            period_sums = {}
                            
                            for m in metric_info:
                                for idx in df.index:
                                    if len(idx) >= 2 and idx[1] == m['description'] and len(idx) == 4 and pd.isna(idx[3]):
                                        metric_data = df.loc[idx]
                                        
                                        # Filter periods
                                        if period_type == "Annual":
                                            periods = [p for p in metric_data.index if p.startswith('FY')]
                                        else:
                                            periods = [p for p in metric_data.index if p.startswith('Q')]
                                        
                                        # Add to sums
                                        for period in periods:
                                            value = metric_data[period]
                                            if pd.notna(value):
                                                if period not in period_sums:
                                                    period_sums[period] = 0
                                                period_sums[period] += value
                                        break
                            
                            # Add summed data points
                            for period, value in period_sums.items():
                                # Convert to millions if needed
                                if abs(value) >= 1000000:
                                    value = value / 1000000
                                chart_data.append({
                                    'Company': ticker,
                                    'Period': period,
                                    'Value': value
                                })
                        
                        else:
                            # Single metric (legacy)
                            for idx in df.index:
                                if len(idx) >= 2 and idx[1] == metric_info['description'] and len(idx) == 4 and pd.isna(idx[3]):
                                    metric_data = df.loc[idx]
                                    
                                    if period_type == "Annual":
                                        periods = [p for p in metric_data.index if p.startswith('FY')]
                                    else:
                                        periods = [p for p in metric_data.index if p.startswith('Q')]
                                    
                                    for period in periods:
                                        value = metric_data[period]
                                        if pd.notna(value):
                                            if abs(value) >= 1000000:
                                                value = value / 1000000
                                            chart_data.append({
                                                'Company': ticker,
                                                'Period': period,
                                                'Value': value
                                            })
                                    break
                
                if chart_data:
                    chart_df = pd.DataFrame(chart_data)
                    
                    # Determine if values need mm suffix
                    needs_mm = any(abs(v) >= 1000000 for v in chart_df['Value'])
                    y_label = add_mm_suffix(selected_group_name, needs_mm)
                    
                    # Create line chart using utility function
                    fig = create_line_chart(
                        chart_df,
                        x_col='Period',
                        y_col='Value',
                        color_col='Company',
                        title=f"{selected_group_name} Comparison ({period_type})",
                        y_label=y_label,
                        period_type=period_type
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Growth analysis
                    st.subheader("Growth Analysis")
                    
                    growth_tabs = st.tabs(["QoQ Growth", "YoY Growth"])
                    
                    with growth_tabs[0]:  # QoQ
                        if period_type == "Quarterly":
                            qoq_data = []
                            
                            for ticker, metric_info in selected_group['metrics'].items():
                                if metric_info and ticker in all_company_data:
                                    df = all_company_data[ticker]
                                    
                                    # Find QoQ growth data
                                    # Handle both single metric (dict) and multiple metrics (list)
                                    if isinstance(metric_info, dict):
                                        metric_descriptions = [metric_info['description']]
                                    else:
                                        metric_descriptions = [m['description'] for m in metric_info]
                                    
                                    for idx in df.index:
                                        if (len(idx) >= 2 and idx[1] in metric_descriptions and 
                                            len(idx) == 4 and pd.notna(idx[3]) and 'qoq growth' in idx[3]):
                                            growth_data = df.loc[idx]
                                            
                                            # Get quarterly periods
                                            periods = [p for p in growth_data.index if p.startswith('Q')]
                                            
                                            for period in periods:
                                                value = growth_data[period]
                                                if pd.notna(value):
                                                    qoq_data.append({
                                                        'Company': ticker,
                                                        'Period': period,
                                                        'Growth %': value
                                                    })
                                            break
                            
                            if qoq_data:
                                qoq_df = pd.DataFrame(qoq_data)
                                
                                # Create bar chart using utility function
                                fig_qoq = create_bar_chart(
                                    qoq_df,
                                    x_col='Period',
                                    y_col='Growth %',
                                    color_col='Company',
                                    title="Quarter-over-Quarter Growth %",
                                    barmode='group'
                                )
                                st.plotly_chart(fig_qoq, use_container_width=True)
                            else:
                                st.info("No QoQ growth data available")
                        else:
                            st.info("QoQ growth is only available for quarterly data")
                    
                    with growth_tabs[1]:  # YoY
                        yoy_data = []
                        
                        for ticker, metric_info in selected_group['metrics'].items():
                            if metric_info and ticker in all_company_data:
                                df = all_company_data[ticker]
                                
                                # Find YoY growth data
                                # Handle both single metric (dict) and multiple metrics (list)
                                if isinstance(metric_info, dict):
                                    metric_descriptions = [metric_info['description']]
                                else:
                                    metric_descriptions = [m['description'] for m in metric_info]
                                
                                for idx in df.index:
                                    if (len(idx) >= 2 and idx[1] in metric_descriptions and 
                                        len(idx) == 4 and pd.notna(idx[3]) and 'yoy growth' in idx[3]):
                                        growth_data = df.loc[idx]
                                        
                                        # Get appropriate periods
                                        if period_type == "Annual":
                                            periods = [p for p in growth_data.index if p.startswith('FY')]
                                        else:
                                            periods = [p for p in growth_data.index if p.startswith('Q')]
                                        
                                        for period in periods:
                                            value = growth_data[period]
                                            if pd.notna(value):
                                                yoy_data.append({
                                                    'Company': ticker,
                                                    'Period': period,
                                                    'Growth %': value
                                                })
                                        break
                        
                        if yoy_data:
                            yoy_df = pd.DataFrame(yoy_data)
                            
                            # Create bar chart using utility function
                            fig_yoy = create_bar_chart(
                                yoy_df,
                                x_col='Period',
                                y_col='Growth %',
                                color_col='Company',
                                title=f"Year-over-Year Growth % ({period_type})",
                                barmode='group'
                            )
                            st.plotly_chart(fig_yoy, use_container_width=True)
                        else:
                            st.info("No YoY growth data available")
                else:
                    st.warning("No data available for charting")
            else:
                st.info("No metric groups available. Create metric groups in the Data Table tab first.")
        
        with display_tab3:
            st.write("### Download Options")
            
            # Prepare data for multi-sheet Excel
            if all_company_data:
                # Create formatted DataFrames for each company
                excel_data = {}
                
                for ticker, df in all_company_data.items():
                    # Format data for Excel (similar to single company logic)
                    excel_df = df.copy()
                    
                    # Create new index without KPI codes
                    new_index = []
                    for idx in excel_df.index:
                        if len(idx) == 4 and pd.isna(idx[3]):
                            new_index.append(idx[1])  # Just description
                        elif len(idx) == 4 and pd.notna(idx[3]):
                            new_index.append(f"{idx[1]} - {idx[3]}")  # Description + growth type
                    
                    excel_df.index = new_index
                    excel_data[ticker] = excel_df
                
                # Download button
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"financial_data_comparison_{timestamp}.xlsx"
                    
                    excel_bytes, suggested_filename = to_excel_multi_sheets(excel_data, filename)
                    
                    st.download_button(
                        label="📊 Download All Companies (Excel)",
                        data=excel_bytes,
                        file_name=suggested_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                with col2:
                    st.info(f"Each company will be in a separate sheet")
            else:
                st.warning("No data available for download")
        
    else:
        # Single company mode (existing logic)
        df = st.session_state.fetched_data
        
        # Display options
        display_tab1, display_tab2, display_tab3 = st.tabs(["📋 Data Table", "📊 Interactive Charts", "💾 Download"])
        
        with display_tab1:
            # Table customization options
            with st.expander("⚙️ Customize Table Display"):
                # Get all base metrics (without growth rows)
                base_metrics = []
                base_metric_labels = []
                for idx in df.index:
                    if len(idx) == 4 and pd.isna(idx[3]):
                        base_metrics.append(idx)
                        # Create label with mm suffix if needed
                        desc = idx[1]
                        row_values = df.loc[idx]
                        if any(abs(val) >= 1000000 for val in row_values if pd.notna(val)) and ", mm" not in desc:
                            desc = f"{desc}, mm"
                        base_metric_labels.append(desc)
                
                st.write("**Select metrics to display:**")
                
                # Select/Deselect all buttons
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("Select All"):
                        for metric in base_metrics:
                            st.session_state[f"metric_{metric[0]}"] = True
                        st.rerun()
                with col2:
                    if st.button("Deselect All"):
                        for metric in base_metrics:
                            st.session_state[f"metric_{metric[0]}"] = False
                        st.rerun()
                
                # Initialize metric order in session state
                if 'metric_display_order' not in st.session_state:
                    st.session_state.metric_display_order = [m[0] for m in base_metrics]
            
                # Create two columns for selection and ordering
                col_select, col_order = st.columns([1, 1])
                
                with col_select:
                    st.write("**Select metrics:**")
                    
                    # Create checkboxes for each metric
                    selected_metric_indices = []
                    for metric, label in zip(base_metrics, base_metric_labels):
                        # Check if key exists in session state, default to True
                        default_value = st.session_state.get(f"metric_{metric[0]}", True)
                        if st.checkbox(label, value=default_value, key=f"metric_{metric[0]}"):
                            selected_metric_indices.append(metric[0])
                
                with col_order:
                    st.write("**Display order (top to bottom):**")
                    
                    # Show current order of selected metrics
                    ordered_metrics = []
                    # First add metrics in the saved order
                    for metric_id in st.session_state.metric_display_order:
                        if metric_id in selected_metric_indices:
                            # Find the metric and label
                            for metric, label in zip(base_metrics, base_metric_labels):
                                if metric[0] == metric_id:
                                    ordered_metrics.append((metric, label))
                                    break
                    
                    # Add any new selected metrics not in the order yet
                    for metric, label in zip(base_metrics, base_metric_labels):
                        if metric[0] in selected_metric_indices and metric[0] not in st.session_state.metric_display_order:
                            ordered_metrics.append((metric, label))
                            st.session_state.metric_display_order.append(metric[0])
                    
                    # Display with move buttons
                    for i, (metric, label) in enumerate(ordered_metrics):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"{i+1}. {label}")
                        with col2:
                            if i > 0 and st.button("↑", key=f"up_{metric[0]}"):
                                # Swap with previous
                                order = st.session_state.metric_display_order[:]
                                idx = order.index(metric[0])
                                order[idx], order[idx-1] = order[idx-1], order[idx]
                                st.session_state.metric_display_order = order
                                st.rerun()
                        with col3:
                            if i < len(ordered_metrics) - 1 and st.button("↓", key=f"down_{metric[0]}"):
                                # Swap with next
                                order = st.session_state.metric_display_order[:]
                                idx = order.index(metric[0])
                                order[idx], order[idx+1] = order[idx+1], order[idx]
                                st.session_state.metric_display_order = order
                                st.rerun()
                
                selected_metrics = ordered_metrics
                
                st.write("**Growth metrics display:**")
                col1, col2 = st.columns(2)
                with col1:
                    show_qoq = st.checkbox("Show Quarter-over-Quarter growth", value=True)
                with col2:
                    show_yoy = st.checkbox("Show Year-over-Year growth", value=True)
        
            # Filter dataframe based on selection
            if selected_metrics:
                # Extract just the indices from selected tuples
                selected_indices = [item[0] for item in selected_metrics]
                
                # Use table component to prepare display dataframe
                display_df = prepare_display_dataframe(
                    df, 
                    selected_indices,
                    show_qoq=show_qoq,
                    show_yoy=show_yoy
                )
            else:
                st.warning("Please select at least one metric to display")
                display_df = pd.DataFrame()  # Empty dataframe
            
            # Format table for display using table component
            if not display_df.empty:
                formatted_df = format_table_for_display(
                    display_df,
                    show_qoq=show_qoq,
                    show_yoy=show_yoy
                )
            else:
                formatted_df = display_df
            
            # Display without styling
            st.dataframe(
                formatted_df,
                use_container_width=True,
                height=600,
                column_config={c: st.column_config.NumberColumn(format="%.2f") for c in formatted_df.select_dtypes('number').columns}
            )
    
    with display_tab2:
        # Period type selection
        col1, col2 = st.columns([1, 3])
        with col1:
            period_type = st.radio("Select Period Type", ["Annual", "Quarterly"])
        
        # Select metric to visualize
        base_metrics = [idx for idx in df.index if len(idx) == 4 and pd.isna(idx[3])]
        
        if base_metrics:
            # Add ", mm" suffix to metric descriptions in dropdown if needed
            def format_metric(idx):
                desc = idx[1]
                # Check if this metric has values >= 1M
                row_values = df.loc[idx]
                if any(abs(val) >= 1000000 for val in row_values if pd.notna(val)) and ", mm" not in desc:
                    desc = f"{desc}, mm"
                return f"{desc} ({idx[2]})"
            
            selected_metric_idx = st.selectbox(
                "Select Metric to Visualize",
                base_metrics,
                format_func=format_metric
            )
            
            # Get data for selected metric
            metric_data = df.loc[selected_metric_idx]
            
            # Filter periods based on selection
            if period_type == "Annual":
                # Only keep FY periods
                filtered_periods = [p for p in metric_data.index if p.startswith('FY')]
            else:
                # Only keep Q periods
                filtered_periods = [p for p in metric_data.index if p.startswith('Q')]
            
            # Get filtered data
            periods = filtered_periods
            values = [metric_data[p] for p in filtered_periods]
            
            # Filter out NaN values
            plot_data = [(p, v) for p, v in zip(periods, values) if pd.notna(v)]
            
            if plot_data:
                # Reverse to show most recent on the left
                plot_data = list(reversed(plot_data))
                periods, values = zip(*plot_data)
                
                # Create figure
                fig = go.Figure()
                
                # Add main metric line
                fig.add_trace(go.Scatter(
                    x=periods,
                    y=values,
                    mode='lines+markers',
                    name=selected_metric_idx[1],
                    line=dict(width=3),
                    marker=dict(size=8)
                ))
                
                # Add vertical lines for year boundaries in quarterly view
                if period_type == "Quarterly" and len(periods) > 0:
                    # Find year transitions
                    year_transitions = []
                    last_year = periods[0].split('-')[1]
                    
                    for i, period in enumerate(periods[1:], 1):
                        current_year = period.split('-')[1]
                        if current_year != last_year:
                            # Add line between periods
                            year_transitions.append((i-0.5, f"{current_year}"))
                            last_year = current_year
                    
                    # Add vertical lines for year transitions
                    for position, year in year_transitions:
                        fig.add_vline(
                            x=position,
                            line_dash="dash",
                            line_color="gray",
                            annotation_text=year,
                            annotation_position="top"
                        )
                
                # Update layout with proper title (including ", mm" if needed)
                title_desc = selected_metric_idx[1]
                row_values = df.loc[selected_metric_idx]
                if any(abs(val) >= 1000000 for val in row_values if pd.notna(val)) and ", mm" not in title_desc:
                    title_desc = f"{title_desc}, mm"
                
                fig.update_layout(
                    title=f"{title_desc} - {company['name']} ({period_type} View)",
                    xaxis_title="Period",
                    yaxis_title=selected_metric_idx[2],
                    hovermode='x unified',
                    height=500
                )
                
                # Add number formatting
                if selected_metric_idx[2] == 'USD':
                    fig.update_layout(yaxis_tickformat=",.0f")
                elif selected_metric_idx[2] == 'Percentage':
                    fig.update_layout(yaxis_tickformat=".1%")
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Growth metrics
                st.subheader("Growth Analysis")
                
                # Show info about period count
                st.info(f"Showing {len(plot_data)} {period_type.lower()} periods")
                
                if period_type == "Quarterly":
                    # Show both QoQ and YoY for quarterly data
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # QoQ growth
                        qoq_idx = selected_metric_idx[:-1] + ('qoq growth',)
                        if qoq_idx in df.index:
                            qoq_data = df.loc[qoq_idx]
                            # Filter to quarterly periods only
                            qoq_plot = [(p, v) for p, v in zip(qoq_data.index, qoq_data.values) 
                                       if pd.notna(v) and p.startswith('Q')]
                            
                            if qoq_plot:
                                # Reverse for consistent ordering
                                qoq_plot = list(reversed(qoq_plot))
                                periods, values = zip(*qoq_plot)
                                fig_qoq = px.bar(x=periods, y=values, 
                                               title="Quarter-over-Quarter Growth %",
                                               labels={'x': 'Period', 'y': 'Growth %'})
                                fig_qoq.update_layout(yaxis_tickformat=".1f")
                                
                                # Add year separators
                                last_year = periods[0].split('-')[1]
                                for i, period in enumerate(periods[1:], 1):
                                    current_year = period.split('-')[1]
                                    if current_year != last_year:
                                        fig_qoq.add_vline(
                                            x=i-0.5,
                                            line_dash="dot",
                                            line_color="lightgray"
                                        )
                                        last_year = current_year
                                
                                st.plotly_chart(fig_qoq, use_container_width=True)
                    
                    with col2:
                        # YoY growth for quarterly
                        yoy_idx = selected_metric_idx[:-1] + ('yoy growth',)
                        if yoy_idx in df.index:
                            yoy_data = df.loc[yoy_idx]
                            # Filter to quarterly periods only
                            yoy_plot = [(p, v) for p, v in zip(yoy_data.index, yoy_data.values) 
                                       if pd.notna(v) and p.startswith('Q')]
                            
                            if yoy_plot:
                                # Reverse for consistent ordering
                                yoy_plot = list(reversed(yoy_plot))
                                periods, values = zip(*yoy_plot)
                                fig_yoy = px.bar(x=periods, y=values, 
                                               title="Year-over-Year Growth % (Quarterly)",
                                               labels={'x': 'Period', 'y': 'Growth %'})
                                fig_yoy.update_layout(yaxis_tickformat=".1f")
                                
                                # Add year separators
                                last_year = periods[0].split('-')[1]
                                for i, period in enumerate(periods[1:], 1):
                                    current_year = period.split('-')[1]
                                    if current_year != last_year:
                                        fig_yoy.add_vline(
                                            x=i-0.5,
                                            line_dash="dot",
                                            line_color="lightgray"
                                        )
                                        last_year = current_year
                                
                                st.plotly_chart(fig_yoy, use_container_width=True)
                else:
                    # Annual data - only show YoY
                    yoy_idx = selected_metric_idx[:-1] + ('yoy growth',)
                    if yoy_idx in df.index:
                        yoy_data = df.loc[yoy_idx]
                        # Filter to annual periods only
                        yoy_plot = [(p, v) for p, v in zip(yoy_data.index, yoy_data.values) 
                                   if pd.notna(v) and p.startswith('FY')]
                        
                        if yoy_plot:
                            # Reverse for consistent ordering
                            yoy_plot = list(reversed(yoy_plot))
                            periods, values = zip(*yoy_plot)
                            fig_yoy = px.bar(x=periods, y=values, 
                                           title="Year-over-Year Growth % (Annual)",
                                           labels={'x': 'Period', 'y': 'Growth %'})
                            fig_yoy.update_layout(yaxis_tickformat=".1f")
                            st.plotly_chart(fig_yoy, use_container_width=True)
    
    with display_tab3:
        st.write("### Download Options")
        
        # Only Excel download button
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            # Excel download
            excel_buffer = BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Format data for Excel (similar to display)
                excel_df = df.copy()
                
                # Create new index without KPI codes
                new_index = []
                for idx in excel_df.index:
                    if len(idx) == 4 and pd.isna(idx[3]):
                        new_index.append(idx[1])  # Just description
                    elif len(idx) == 4 and pd.notna(idx[3]):
                        new_index.append(f"{idx[1]} - {idx[3]}")  # Description + growth type
                
                excel_df.index = new_index
                
                # Write to Excel
                excel_df.to_excel(writer, sheet_name=st.session_state.selected_ticker)
                
                # Format cells
                worksheet = writer.sheets[st.session_state.selected_ticker]
                
                # Apply number formatting
                for row_num, row_name in enumerate(excel_df.index, start=2):  # Start from row 2 (after header)
                    for col_num in range(1, len(excel_df.columns) + 1):  # Skip index column
                        cell = worksheet.cell(row=row_num, column=col_num + 1)  # +1 for index column
                        
                        if cell.value and isinstance(cell.value, (int, float)):
                            if "qoq growth" in row_name or "yoy growth" in row_name:
                                cell.number_format = '0.0%'
                                cell.value = cell.value / 100  # Convert to percentage
                            else:
                                cell.number_format = '#,##0'
                
                # Write metadata
                metadata_df = pd.DataFrame({
                    'Company': [company['name']],
                    'Ticker': [st.session_state.selected_ticker],
                    'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    'Total Metrics': [len(st.session_state.selected_kpis)]
                })
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            st.download_button(
                label="📊 Download as Excel",
                data=excel_buffer.getvalue(),
                file_name=f"{st.session_state.selected_ticker}_financial_data_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# Footer
st.markdown("---")
st.markdown("Data powered by Canalyst/Tegus API | Built with Streamlit")