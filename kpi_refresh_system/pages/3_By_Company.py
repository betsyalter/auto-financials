"""
By Company Page - Analyze all metrics for a single company
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.kpi_service import KPIService
from src.components.charts import create_line_chart, create_bar_chart
from src.components.tables import (
    prepare_display_dataframe, format_table_for_display,
    prepare_excel_export_data
)
from src.display_utils import format_dataframe_for_display
from main import KPIRefreshApp
import tenacity
import requests

st.set_page_config(
    page_title="By Company - KPI Dashboard",
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

st.title("🏢 Analyze by Company")
st.markdown("### View all metrics for a single company")

# Check if single company is selected
if st.session_state.get('is_multi_company') or not st.session_state.get('company_data'):
    st.warning("⚠️ Please select a single company first!")
    st.info("👈 Go to **'Select Tickers'** page and enter a single ticker (e.g., AAPL)")
    st.stop()

# Display company info
company = st.session_state.company_data
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Company Name", company['name'])
with col2:
    st.metric("Ticker", st.session_state.selected_ticker)
with col3:
    st.metric("Sector", company.get('sector', {}).get('path', 'N/A').split(':')[-1])

st.markdown("---")

# Metric Discovery
st.markdown("### Step 1: Discover Available Metrics")

col1, col2 = st.columns([3, 1])
with col1:
    if 'available_metrics' in st.session_state:
        st.success(f"✅ {len(st.session_state.available_metrics)} metrics available")
with col2:
    if st.button("🔄 Discover Metrics", type="primary"):
        with st.spinner("Fetching available metrics..."):
            try:
                # Clear previous selections
                st.session_state.selected_kpis = []
                st.session_state.fetched_data = None
                if 'metric_display_order' in st.session_state:
                    del st.session_state.metric_display_order
                
                # Get latest model
                model = st.session_state.app.client.get_latest_equity_model(company['company_id'])
                model_version = model['model_version']['name']
                
                # Get all time series
                all_time_series = st.session_state.app.client.list_time_series(
                    company['company_id'],
                    model_version,
                    is_kpi=None
                )
                
                st.session_state.available_metrics = all_time_series
                st.session_state.model_version = model_version
                st.success(f"Found {len(all_time_series)} available metrics!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error fetching metrics: {str(e)}")

# Metric Selection
if 'available_metrics' in st.session_state:
    st.markdown("### Step 2: Select Metrics")
    
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
            
            # Display metrics with checkboxes
            for ts in categories[selected_category][:20]:
                if st.checkbox(
                    f"{ts['description']} ({ts['unit']['description']})",
                    value=ts in st.session_state.selected_kpis,
                    key=f"cat_{ts['slug']}"
                ):
                    if ts not in st.session_state.selected_kpis:
                        st.session_state.selected_kpis.append(ts)
                else:
                    if ts in st.session_state.selected_kpis:
                        st.session_state.selected_kpis.remove(ts)
            
            if len(categories[selected_category]) > 20:
                st.info(f"Showing first 20 of {len(categories[selected_category])} metrics. Use search for more.")
    
    with tab2:
        search_term = st.text_input("Search for metrics (e.g., 'revenue', 'margin', 'growth')")
        
        if search_term:
            # Search in descriptions and names
            matching = [
                ts for ts in st.session_state.available_metrics
                if search_term.lower() in ts['description'].lower() or
                any(search_term.lower() in name.lower() for name in ts['names'])
            ]
            
            st.write(f"**Found {len(matching)} matching metrics:**")
            
            for ts in matching[:20]:
                if st.checkbox(
                    f"{ts['description']} ({ts['unit']['description']})",
                    value=ts in st.session_state.selected_kpis,
                    key=f"search_{ts['slug']}"
                ):
                    if ts not in st.session_state.selected_kpis:
                        st.session_state.selected_kpis.append(ts)
                else:
                    if ts in st.session_state.selected_kpis:
                        st.session_state.selected_kpis.remove(ts)
    
    with tab3:
        st.write("**Select common financial KPIs:**")
        
        # Common KPI keywords
        common_keywords = [
            ('Total Revenue', 'total revenue'),
            ('Gross Profit', 'gross profit'),
            ('Operating Income', 'operating income'),
            ('Net Income', 'net income'),
            ('EPS', 'eps'),
            ('Free Cash Flow', 'free cash flow'),
            ('Gross Margin', 'gross margin'),
            ('Operating Margin', 'operating margin'),
            ('EBITDA', 'ebitda')
        ]
        
        for display_name, keyword in common_keywords:
            matching = [
                ts for ts in st.session_state.available_metrics
                if keyword in ts['description'].lower()
            ]
            
            if matching:
                ts = matching[0]  # Take first match
                if st.checkbox(
                    f"{display_name}: {ts['description']} ({ts['unit']['description']})",
                    value=ts in st.session_state.selected_kpis,
                    key=f"common_{keyword.replace(' ', '_')}"
                ):
                    if ts not in st.session_state.selected_kpis:
                        st.session_state.selected_kpis.append(ts)
                else:
                    if ts in st.session_state.selected_kpis:
                        st.session_state.selected_kpis.remove(ts)
    
    with tab4:
        st.write("**Enter metric names directly (one per line):**")
        
        manual_metrics = st.text_area(
            "Metric names",
            placeholder="Revenue\nGross Profit\nOperating Income",
            height=200
        )
        
        if st.button("Add Manual Metrics"):
            if manual_metrics:
                lines = manual_metrics.strip().split('\n')
                added_count = 0
                
                for line in lines:
                    search_term = line.strip()
                    if search_term:
                        # Find matching metrics
                        matching = [
                            ts for ts in st.session_state.available_metrics
                            if search_term.lower() in ts['description'].lower()
                        ]
                        
                        if matching and matching[0] not in st.session_state.selected_kpis:
                            st.session_state.selected_kpis.append(matching[0])
                            added_count += 1
                
                if added_count > 0:
                    st.success(f"Added {added_count} metrics")
                    st.rerun()
                else:
                    st.warning("No new matching metrics found")
    
    # Show selected metrics summary
    if st.session_state.selected_kpis:
        st.markdown("---")
        st.markdown("### Selected Metrics")
        st.info(f"You have selected {len(st.session_state.selected_kpis)} metrics")
        
        # Show selected metrics in expander
        with st.expander("View selected metrics"):
            for i, ts in enumerate(st.session_state.selected_kpis):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{i+1}. {ts['description']} ({ts['unit']['description']})")
                with col2:
                    if st.button("Remove", key=f"remove_{ts['slug']}"):
                        st.session_state.selected_kpis.remove(ts)
                        st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All Metrics"):
                st.session_state.selected_kpis = []
                st.rerun()
        
        with col2:
            if st.button("📊 Fetch Data", type="primary"):
                with st.spinner("Fetching financial data..."):
                    try:
                        # Prepare KPI DataFrame
                        temp_kpi_df = st.session_state.kpi_service.prepare_single_company_kpis(
                            company['company_id'],
                            st.session_state.selected_kpis
                        )
                        
                        # Fetch data
                        df = st.session_state.kpi_service.fetch_kpi_data(
                            company['company_id'],
                            temp_kpi_df,
                            st.session_state.model_version
                        )
                        
                        st.session_state.fetched_data = df
                        st.success("Data fetched successfully!")
                        
                    except Exception as e:
                        if isinstance(e, (tenacity.RetryError, requests.ConnectionError)):
                            st.error("Connection problem fetching data.")
                            if st.button("🔁 Retry", key="retry_fetch"):
                                st.rerun()
                        else:
                            st.error(f"Error fetching data: {str(e)}")

# Display Data
if st.session_state.get('fetched_data') is not None and not st.session_state.get('is_multi_company'):
    st.markdown("---")
    st.markdown("### Step 3: View Results")
    
    df = st.session_state.fetched_data
    
    # Display tabs
    display_tab1, display_tab2, display_tab3 = st.tabs(["📋 Data Table", "📊 Interactive Charts", "💾 Download"])
    
    with display_tab1:
        # Table customization options
        with st.expander("⚙️ Customize Table Display"):
            # Get all base metrics
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
            
            # Initialize metric order
            if 'metric_display_order' not in st.session_state:
                st.session_state.metric_display_order = [m[0] for m in base_metrics]
            
            # Create two columns for selection and ordering
            col_select, col_order = st.columns([1, 1])
            
            with col_select:
                st.write("**Select metrics:**")
                
                selected_metric_indices = []
                for metric, label in zip(base_metrics, base_metric_labels):
                    default_value = st.session_state.get(f"metric_{metric[0]}", True)
                    if st.checkbox(label, value=default_value, key=f"metric_{metric[0]}"):
                        selected_metric_indices.append(metric[0])
            
            with col_order:
                st.write("**Display order (drag to reorder):**")
                
                # Show current order of selected metrics
                ordered_metrics = []
                # First add metrics in saved order
                for metric_id in st.session_state.metric_display_order:
                    if metric_id in selected_metric_indices:
                        for metric, label in zip(base_metrics, base_metric_labels):
                            if metric[0] == metric_id:
                                ordered_metrics.append((metric, label))
                                break
                
                # Add any new selected metrics
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
                            order = st.session_state.metric_display_order[:]
                            idx = order.index(metric[0])
                            order[idx], order[idx-1] = order[idx-1], order[idx]
                            st.session_state.metric_display_order = order
                            st.rerun()
                    with col3:
                        if i < len(ordered_metrics) - 1 and st.button("↓", key=f"down_{metric[0]}"):
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
            selected_indices = [item[0] for item in selected_metrics]
            
            # Use table component to prepare display
            display_df = prepare_display_dataframe(
                df,
                selected_indices,
                show_qoq=show_qoq,
                show_yoy=show_yoy
            )
        else:
            st.warning("Please select at least one metric to display")
            display_df = pd.DataFrame()
        
        # Format table for display
        if not display_df.empty:
            formatted_df = format_table_for_display(
                display_df,
                show_qoq=show_qoq,
                show_yoy=show_yoy
            )
        else:
            formatted_df = display_df
        
        # Display table
        st.dataframe(
            formatted_df,
            use_container_width=True,
            height=600,
            column_config={
                c: st.column_config.NumberColumn(format="%.2f")
                for c in formatted_df.select_dtypes('number').columns
            }
        )
    
    with display_tab2:
        # Period type selection
        col1, col2 = st.columns([1, 3])
        with col1:
            period_type = st.radio("Select Period Type", ["Annual", "Quarterly"])
        
        # Select metric to visualize
        base_metrics = [idx for idx in df.index if len(idx) == 4 and pd.isna(idx[3])]
        
        if base_metrics:
            # Format metric names for dropdown
            def format_metric(idx):
                desc = idx[1]
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
            
            # Filter periods
            if period_type == "Annual":
                filtered_periods = [p for p in metric_data.index if p.startswith('FY')]
            else:
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
                    year_transitions = []
                    last_year = periods[0].split('-')[1]
                    
                    for i, period in enumerate(periods[1:], 1):
                        current_year = period.split('-')[1]
                        if current_year != last_year:
                            year_transitions.append((i-0.5, f"{current_year}"))
                            last_year = current_year
                    
                    for position, year in year_transitions:
                        fig.add_vline(
                            x=position,
                            line_dash="dash",
                            line_color="gray",
                            annotation_text=year,
                            annotation_position="top"
                        )
                
                # Update layout
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
                st.info(f"Showing {len(plot_data)} {period_type.lower()} periods")
                
                if period_type == "Quarterly":
                    # Show both QoQ and YoY
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # QoQ growth
                        qoq_idx = selected_metric_idx[:-1] + ('qoq growth',)
                        if qoq_idx in df.index:
                            qoq_data = df.loc[qoq_idx]
                            qoq_plot = [
                                (p, v) for p, v in zip(qoq_data.index, qoq_data.values)
                                if pd.notna(v) and p.startswith('Q')
                            ]
                            
                            if qoq_plot:
                                qoq_plot = list(reversed(qoq_plot))
                                periods, values = zip(*qoq_plot)
                                
                                fig_qoq = px.bar(
                                    x=periods, y=values,
                                    title="Quarter-over-Quarter Growth %",
                                    labels={'x': 'Period', 'y': 'Growth %'}
                                )
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
                            yoy_plot = [
                                (p, v) for p, v in zip(yoy_data.index, yoy_data.values)
                                if pd.notna(v) and p.startswith('Q')
                            ]
                            
                            if yoy_plot:
                                yoy_plot = list(reversed(yoy_plot))
                                periods, values = zip(*yoy_plot)
                                
                                fig_yoy = px.bar(
                                    x=periods, y=values,
                                    title="Year-over-Year Growth % (Quarterly)",
                                    labels={'x': 'Period', 'y': 'Growth %'}
                                )
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
                        yoy_plot = [
                            (p, v) for p, v in zip(yoy_data.index, yoy_data.values)
                            if pd.notna(v) and p.startswith('FY')
                        ]
                        
                        if yoy_plot:
                            yoy_plot = list(reversed(yoy_plot))
                            periods, values = zip(*yoy_plot)
                            
                            fig_yoy = px.bar(
                                x=periods, y=values,
                                title="Year-over-Year Growth % (Annual)",
                                labels={'x': 'Period', 'y': 'Growth %'}
                            )
                            fig_yoy.update_layout(yaxis_tickformat=".1f")
                            st.plotly_chart(fig_yoy, use_container_width=True)
    
    with display_tab3:
        st.write("### Download Options")
        
        # Excel download
        excel_buffer = BytesIO()
        
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # Format data for Excel
            excel_df = prepare_excel_export_data(df)
            
            # Write to Excel
            excel_df.to_excel(writer, sheet_name=st.session_state.selected_ticker)
            
            # Format cells
            worksheet = writer.sheets[st.session_state.selected_ticker]
            
            # Apply number formatting
            for row_num, row_name in enumerate(excel_df.index, start=2):
                for col_num in range(1, len(excel_df.columns) + 1):
                    cell = worksheet.cell(row=row_num, column=col_num + 1)
                    
                    if cell.value and isinstance(cell.value, (int, float)):
                        if "qoq growth" in row_name or "yoy growth" in row_name:
                            cell.number_format = '0.0%'
                            cell.value = cell.value / 100
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
        
        excel_buffer.seek(0)
        
        # Create suggested filename
        company_safe_name = "".join(c for c in company['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        suggested_filename = f"{company_safe_name}_{st.session_state.selected_ticker}_financial_data_{timestamp}.xlsx"
        
        st.download_button(
            label="📥 Download Excel",
            data=excel_buffer,
            file_name=suggested_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )