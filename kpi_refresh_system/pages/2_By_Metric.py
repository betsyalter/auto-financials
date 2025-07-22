"""
By Metric Page - Compare metrics across multiple companies
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from io import BytesIO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.kpi_service import KPIService
from src.components.charts import (
    create_multi_company_comparison_chart,
    create_growth_comparison_chart
)
from src.components.tables import format_table_for_display
from src.display_utils import format_dataframe_for_display, create_period_columns
from src.utils.export_utils import to_excel_multi_sheets
from main import KPIRefreshApp
import tenacity
import requests

st.set_page_config(
    page_title="By Metric - KPI Dashboard", 
    page_icon="📊",
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

st.title("📊 Compare by Metric")
st.markdown("### Compare the same metrics across multiple companies")

# Check if multiple companies are selected
if not st.session_state.get('is_multi_company') or not st.session_state.get('companies_data'):
    st.warning("⚠️ Please select multiple companies first!")
    st.info("👈 Go to **'Select Tickers'** page and enter comma-separated tickers (e.g., AAPL, MSFT, GOOGL)")
    st.stop()

# Display selected companies
st.markdown("#### Selected Companies")
cols = st.columns(min(len(st.session_state.companies_data), 4))
for i, (ticker, company) in enumerate(st.session_state.companies_data.items()):
    with cols[i % 4]:
        st.metric(ticker, company['name'][:30])

st.markdown("---")

# Metric Discovery Section
st.markdown("### Step 1: Discover Metrics")

# Initialize storage
if 'selected_metrics_per_company' not in st.session_state:
    st.session_state.selected_metrics_per_company = {}
if 'all_companies_metrics' not in st.session_state:
    st.session_state.all_companies_metrics = {}
if 'model_versions' not in st.session_state:
    st.session_state.model_versions = {}

# Create tabs for each company
company_tabs = st.tabs([f"{ticker}: {company['name'][:30]}" 
                       for ticker, company in st.session_state.companies_data.items()])

for tab_idx, (ticker, company) in enumerate(st.session_state.companies_data.items()):
    with company_tabs[tab_idx]:
        # Initialize selected metrics for this company
        if ticker not in st.session_state.selected_metrics_per_company:
            st.session_state.selected_metrics_per_company[ticker] = []
        
        # Discover metrics button
        col1, col2 = st.columns([3, 1])
        with col1:
            if ticker in st.session_state.all_companies_metrics:
                st.success(f"✅ {len(st.session_state.all_companies_metrics[ticker])} metrics available")
        with col2:
            if st.button(f"🔄 Discover", key=f"discover_{ticker}"):
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
                        
                        st.session_state.all_companies_metrics[ticker] = time_series
                        st.session_state.model_versions[ticker] = model_version
                        
                        st.success(f"Found {len(time_series)} metrics!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # Show metric selection if available
        if ticker in st.session_state.all_companies_metrics:
            metrics = st.session_state.all_companies_metrics[ticker]
            
            # Selection tabs
            metric_tabs = st.tabs(["📂 By Category", "🔍 Search", "⭐ Common KPIs"])
            
            with metric_tabs[0]:  # By Category
                categories = {}
                for ts in metrics:
                    cat = ts['category']['description']
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(ts)
                
                selected_category = st.selectbox(
                    "Select Category", 
                    sorted(categories.keys()),
                    key=f"cat_select_{ticker}"
                )
                
                if selected_category:
                    st.write(f"**{len(categories[selected_category])} metrics in {selected_category}:**")
                    
                    for ts in categories[selected_category][:20]:
                        checkbox_key = f"{ticker}_cat_{ts['slug']}"
                        is_selected = any(m['slug'] == ts['slug'] 
                                        for m in st.session_state.selected_metrics_per_company[ticker])
                        
                        if st.checkbox(
                            f"{ts['description']} ({ts['unit']['description']})",
                            value=is_selected,
                            key=checkbox_key
                        ):
                            if not is_selected:
                                st.session_state.selected_metrics_per_company[ticker].append(ts)
                        else:
                            st.session_state.selected_metrics_per_company[ticker] = [
                                m for m in st.session_state.selected_metrics_per_company[ticker]
                                if m['slug'] != ts['slug']
                            ]
            
            with metric_tabs[1]:  # Search
                search_term = st.text_input("Search metrics", key=f"search_{ticker}")
                
                if search_term:
                    matching = [
                        ts for ts in metrics
                        if search_term.lower() in ts['description'].lower() or
                        any(search_term.lower() in name.lower() for name in ts['names'])
                    ]
                    
                    st.write(f"**Found {len(matching)} matching metrics:**")
                    
                    for ts in matching[:20]:
                        checkbox_key = f"{ticker}_search_{ts['slug']}"
                        is_selected = any(m['slug'] == ts['slug'] 
                                        for m in st.session_state.selected_metrics_per_company[ticker])
                        
                        if st.checkbox(
                            f"{ts['description']} ({ts['unit']['description']})",
                            value=is_selected,
                            key=checkbox_key
                        ):
                            if not is_selected:
                                st.session_state.selected_metrics_per_company[ticker].append(ts)
                        else:
                            st.session_state.selected_metrics_per_company[ticker] = [
                                m for m in st.session_state.selected_metrics_per_company[ticker]
                                if m['slug'] != ts['slug']
                            ]
            
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
                    matching = [ts for ts in metrics if keyword in ts['description'].lower()]
                    if matching:
                        ts = matching[0]
                        checkbox_key = f"{ticker}_common_{keyword.replace(' ', '_')}"
                        is_selected = any(m['slug'] == ts['slug'] 
                                        for m in st.session_state.selected_metrics_per_company[ticker])
                        
                        if st.checkbox(
                            f"{display_name}: {ts['description']} ({ts['unit']['description']})",
                            value=is_selected,
                            key=checkbox_key
                        ):
                            if not is_selected:
                                st.session_state.selected_metrics_per_company[ticker].append(ts)
                        else:
                            st.session_state.selected_metrics_per_company[ticker] = [
                                m for m in st.session_state.selected_metrics_per_company[ticker]
                                if m['slug'] != ts['slug']
                            ]
            
            # Show selected count
            selected_count = len(st.session_state.selected_metrics_per_company[ticker])
            if selected_count > 0:
                st.info(f"Selected {selected_count} metrics")
                
                if st.button(f"Clear Selection", key=f"clear_{ticker}"):
                    st.session_state.selected_metrics_per_company[ticker] = []
                    st.rerun()

# Metric Groups Section
if any(len(metrics) > 0 for metrics in st.session_state.selected_metrics_per_company.values()):
    st.markdown("---")
    st.markdown("### Step 2: Create Metric Groups")
    st.info("Group similar metrics from different companies for comparison")
    
    # Initialize metric groups
    if 'metric_groups' not in st.session_state:
        st.session_state.metric_groups = []
    
    # Show existing groups
    if st.session_state.metric_groups:
        st.markdown("#### Existing Metric Groups")
        for i, group in enumerate(st.session_state.metric_groups):
            with st.expander(f"📊 {group['name']}", expanded=False):
                for ticker, metric_info in group['metrics'].items():
                    if metric_info:
                        if isinstance(metric_info, list):
                            descriptions = [m['description'] for m in metric_info]
                            combined_desc = " + ".join(descriptions)
                            st.write(f"**{ticker}**: {combined_desc}")
                        else:
                            st.write(f"**{ticker}**: {metric_info['description']}")
                    else:
                        st.write(f"**{ticker}**: *Not selected*")
                
                if st.button("Delete Group", key=f"delete_group_{i}"):
                    st.session_state.metric_groups.pop(i)
                    st.rerun()
    
    # Create new group
    st.markdown("#### Create New Metric Group")
    with st.expander("➕ Add Metric Group", expanded=True):
        group_name = st.text_input("Group Name (e.g., 'Revenue', 'Profit', 'Margins')")
        
        if group_name:
            st.markdown("**Select corresponding metric from each company:**")
            
            new_group_metrics = {}
            cols = st.columns(len(st.session_state.companies_data))
            
            for col_idx, (ticker, company) in enumerate(st.session_state.companies_data.items()):
                with cols[col_idx]:
                    st.markdown(f"**{ticker}**")
                    
                    selected_metrics = st.session_state.selected_metrics_per_company.get(ticker, [])
                    
                    if selected_metrics:
                        selected_for_group = []
                        
                        for m in selected_metrics:
                            if st.checkbox(
                                f"{m['description']}",
                                key=f"group_{ticker}_{group_name}_{m['slug']}"
                            ):
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
                        st.warning(f"No metrics selected")
                        new_group_metrics[ticker] = None
            
            if st.button("Create Metric Group", type="primary"):
                if any(new_group_metrics.values()):
                    st.session_state.metric_groups.append({
                        'name': group_name,
                        'metrics': new_group_metrics
                    })
                    st.success(f"Created metric group: {group_name}")
                    st.rerun()
                else:
                    st.error("Please select at least one metric")
    
    # Fetch data button
    if st.session_state.metric_groups:
        st.markdown("---")
        st.markdown("### Step 3: Fetch Data")
        
        total_metrics = sum(
            len([m for m in group['metrics'].values() if m]) 
            for group in st.session_state.metric_groups
        )
        st.info(f"Ready to fetch data for {len(st.session_state.metric_groups)} metric groups")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All Groups"):
                st.session_state.metric_groups = []
                st.rerun()
        
        with col2:
            if st.button("📊 Fetch Data", type="primary"):
                with st.spinner("Fetching financial data..."):
                    try:
                        all_company_data = {}
                        
                        for ticker, company in st.session_state.companies_data.items():
                            company_id = company['company_id']
                            model_version = st.session_state.model_versions[ticker]
                            
                            # Collect all metrics for this company
                            temp_kpis = []
                            priority = 1
                            
                            for group in st.session_state.metric_groups:
                                if ticker in group['metrics'] and group['metrics'][ticker]:
                                    metric_info = group['metrics'][ticker]
                                    
                                    if isinstance(metric_info, list):
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
                                                'group_name': group['name']
                                            })
                                            priority += 1
                            
                            if temp_kpis:
                                temp_kpi_df = pd.DataFrame(temp_kpis)
                                df = st.session_state.kpi_service.fetch_kpi_data(
                                    company_id, temp_kpi_df, model_version
                                )
                                all_company_data[ticker] = df
                        
                        st.session_state.fetched_data = all_company_data
                        st.session_state.metric_groups_used = st.session_state.metric_groups.copy()
                        st.success(f"Data fetched successfully!")
                        
                    except Exception as e:
                        if isinstance(e, (tenacity.RetryError, requests.ConnectionError)):
                            st.error("Connection problem fetching data.")
                            if st.button("🔁 Retry", key="retry_multi_fetch"):
                                st.rerun()
                        else:
                            st.error(f"Error: {str(e)}")

# Display Data Section
if st.session_state.get('fetched_data') and st.session_state.get('is_multi_company'):
    st.markdown("---")
    st.markdown("### Step 4: View Results")
    
    all_company_data = st.session_state.fetched_data
    
    # Display tabs
    display_tab1, display_tab2, display_tab3 = st.tabs(["📋 Data Table", "📊 Interactive Charts", "💾 Download"])
    
    with display_tab1:
        # Table customization
        with st.expander("⚙️ Customize Table Display"):
            st.write("**Growth metrics display:**")
            col1, col2 = st.columns(2)
            with col1:
                show_qoq = st.checkbox("Show Quarter-over-Quarter growth", value=True)
            with col2:
                show_yoy = st.checkbox("Show Year-over-Year growth", value=True)
        
        st.markdown("#### Comparison by Metric")
        
        # Create comparison tables by metric group
        if 'metric_groups_used' in st.session_state:
            for group in st.session_state.metric_groups_used:
                comparison_data = []
                
                # Check if we need mm suffix
                needs_mm = False
                for ticker, metric_info in group['metrics'].items():
                    if metric_info and ticker in all_company_data:
                        df = all_company_data[ticker]
                        
                        metrics_to_check = metric_info if isinstance(metric_info, list) else [metric_info]
                        
                        for m in metrics_to_check:
                            for idx in df.index:
                                if (len(idx) >= 2 and idx[1] == m['description'] and 
                                    len(idx) == 4 and pd.isna(idx[3])):
                                    row_values = df.loc[idx]
                                    if any(abs(val) >= 1000000 for val in row_values if pd.notna(val)):
                                        needs_mm = True
                                        break
                            if needs_mm:
                                break
                
                # Create comparison rows
                for ticker, metric_info in group['metrics'].items():
                    if metric_info and ticker in all_company_data:
                        df = all_company_data[ticker]
                        
                        if isinstance(metric_info, list):
                            # Multiple metrics - sum them
                            base_values = {}
                            qoq_values = {}
                            yoy_values = {}
                            
                            for m in metric_info:
                                for idx in df.index:
                                    if len(idx) >= 2 and idx[1] == m['description']:
                                        if len(idx) == 4 and pd.isna(idx[3]):
                                            # Base metric
                                            for period in df.columns:
                                                if period not in base_values:
                                                    base_values[period] = 0
                                                val = df.loc[idx, period]
                                                if pd.notna(val):
                                                    base_values[period] += val
                                                else:
                                                    base_values[period] = None if base_values[period] == 0 else base_values[period]
                                        elif len(idx) == 4 and pd.notna(idx[3]):
                                            # Growth metrics
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
                            
                            # Add base row
                            if base_values:
                                row_data = {'Company': ticker, 'Type': ''}
                                row_data.update(base_values)
                                comparison_data.append(row_data)
                            
                            # Add growth rows
                            if show_qoq and qoq_values:
                                qoq_row = {'Company': ticker, 'Type': 'qoq growth'}
                                for period, values in qoq_values.items():
                                    if values:
                                        qoq_row[period] = sum(values) / len(values)
                                    else:
                                        qoq_row[period] = None
                                comparison_data.append(qoq_row)
                            
                            if show_yoy and yoy_values:
                                yoy_row = {'Company': ticker, 'Type': 'yoy growth'}
                                for period, values in yoy_values.items():
                                    if values:
                                        yoy_row[period] = sum(values) / len(values)
                                    else:
                                        yoy_row[period] = None
                                comparison_data.append(yoy_row)
                        
                        else:
                            # Single metric
                            for idx in df.index:
                                if len(idx) >= 2 and idx[1] == metric_info['description']:
                                    if len(idx) == 4 and pd.isna(idx[3]):
                                        row_data = {'Company': ticker, 'Type': ''}
                                    elif len(idx) == 4 and pd.notna(idx[3]):
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
                    
                    # Format display
                    formatted_df = format_dataframe_for_display(
                        comp_df,
                        include_growth={'qoq': show_qoq, 'yoy': show_yoy}
                    )
                    
                    # Add units to group name
                    display_name = group['name']
                    if needs_mm and ", mm" not in display_name:
                        display_name = f"{display_name}, mm"
                    
                    st.markdown(f"**{display_name}**")
                    
                    # Ensure uniqueness
                    if not formatted_df.index.is_unique:
                        formatted_df = formatted_df.reset_index(drop=True)
                    if not formatted_df.columns.is_unique:
                        formatted_df.columns = pd.io.parsers.ParserBase(
                            {'names': formatted_df.columns}
                        )._maybe_dedup_names(formatted_df.columns)
                    
                    st.dataframe(
                        formatted_df,
                        use_container_width=True,
                        column_config={
                            c: st.column_config.NumberColumn(format="%.2f") 
                            for c in formatted_df.select_dtypes('number').columns
                        }
                    )
                    st.markdown("---")
    
    with display_tab2:
        st.markdown("#### Interactive Charts")
        
        # Create chart for each metric group
        if 'metric_groups_used' in st.session_state:
            for group in st.session_state.metric_groups_used:
                # Get the first metric description for this group
                metric_name = None
                for ticker, metric_info in group['metrics'].items():
                    if metric_info:
                        if isinstance(metric_info, list):
                            metric_name = metric_info[0]['description']
                        else:
                            metric_name = metric_info['description']
                        break
                
                if metric_name:
                    st.markdown(f"**{group['name']}**")
                    
                    # Chart type selection
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        chart_type = st.radio(
                            "Chart Type",
                            ["Line", "Bar"],
                            horizontal=True,
                            key=f"chart_type_{group['name']}"
                        )
                    with col2:
                        period_type = st.selectbox(
                            "Period",
                            ["All", "Annual", "Quarterly"],
                            key=f"period_type_{group['name']}"
                        )
                    
                    # Create comparison chart
                    fig = create_multi_company_comparison_chart(
                        all_company_data,
                        metric_name,
                        chart_type.lower(),
                        period_type.lower()
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Growth chart tabs
                    growth_tabs = st.tabs(["QoQ Growth", "YoY Growth"])
                    
                    with growth_tabs[0]:
                        fig_qoq = create_growth_comparison_chart(
                            all_company_data,
                            metric_name,
                            'qoq',
                            period_type.lower()
                        )
                        st.plotly_chart(fig_qoq, use_container_width=True)
                    
                    with growth_tabs[1]:
                        fig_yoy = create_growth_comparison_chart(
                            all_company_data,
                            metric_name,
                            'yoy',
                            period_type.lower()
                        )
                        st.plotly_chart(fig_yoy, use_container_width=True)
                    
                    st.markdown("---")
    
    with display_tab3:
        st.markdown("#### Download Data")
        
        # Prepare data for export
        export_sheets = {}
        
        # Add raw data for each company
        for ticker, df in all_company_data.items():
            export_sheets[f"{ticker}_Raw"] = df
        
        # Add comparison tables by metric group
        if 'metric_groups_used' in st.session_state:
            for group in st.session_state.metric_groups_used:
                comparison_data = []
                
                for ticker, metric_info in group['metrics'].items():
                    if metric_info and ticker in all_company_data:
                        df = all_company_data[ticker]
                        
                        if isinstance(metric_info, list):
                            # Handle multiple metrics
                            base_values = {}
                            for m in metric_info:
                                for idx in df.index:
                                    if (len(idx) >= 2 and idx[1] == m['description'] and 
                                        len(idx) == 4 and pd.isna(idx[3])):
                                        for period in df.columns:
                                            if period not in base_values:
                                                base_values[period] = 0
                                            val = df.loc[idx, period]
                                            if pd.notna(val):
                                                base_values[period] += val
                            
                            if base_values:
                                row_data = {'Company': ticker, 'Metric': group['name']}
                                row_data.update(base_values)
                                comparison_data.append(row_data)
                        else:
                            # Single metric
                            for idx in df.index:
                                if (len(idx) >= 2 and idx[1] == metric_info['description'] and
                                    len(idx) == 4 and pd.isna(idx[3])):
                                    row_data = {'Company': ticker, 'Metric': group['name']}
                                    for period in df.columns:
                                        row_data[period] = df.loc[idx, period]
                                    comparison_data.append(row_data)
                
                if comparison_data:
                    comp_df = pd.DataFrame(comparison_data)
                    comp_df = comp_df.set_index(['Company', 'Metric'])
                    export_sheets[f"Comparison_{group['name']}"] = comp_df
        
        # Create download button
        if export_sheets:
            excel_file = to_excel_multi_sheets(export_sheets)
            
            st.download_button(
                label="📥 Download Excel",
                data=excel_file,
                file_name=f"multi_company_comparison_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )