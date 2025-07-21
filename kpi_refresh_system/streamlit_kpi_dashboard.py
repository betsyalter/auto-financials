import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from pathlib import Path
import requests

st.set_page_config(
    page_title="KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .growth-positive { color: #00cc00; }
    .growth-negative { color: #ff4444; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    """Load KPI data from CSV files"""
    try:
        # Load consolidated data
        df = pd.read_csv('data/csv/consolidated_kpis.csv')
        
        # Convert date columns
        df['period_date'] = pd.to_datetime(df['period_date'])
        
        # Load metadata
        with open('data/csv/metadata.json', 'r') as f:
            metadata = json.load(f)
        
        return df, metadata
    except FileNotFoundError:
        st.error("Data files not found. Please run the KPI refresh first.")
        return None, None

def create_kpi_chart(df, kpi_name, companies):
    """Create a line chart for a specific KPI across companies"""
    fig = go.Figure()
    
    for company in companies:
        company_data = df[(df['ticker'] == company) & (df['kpi_label'] == kpi_name)]
        if not company_data.empty:
            fig.add_trace(go.Scatter(
                x=company_data['period_date'],
                y=company_data['value'],
                mode='lines+markers',
                name=company,
                hovertemplate=f'{company}<br>%{{x}}<br>%{{y:,.0f}}<extra></extra>'
            ))
    
    fig.update_layout(
        title=kpi_name,
        xaxis_title="Period",
        yaxis_title="Value",
        hovermode='x unified',
        height=400
    )
    
    return fig

def display_company_metrics(df, company):
    """Display key metrics for a company"""
    company_data = df[df['ticker'] == company]
    
    if company_data.empty:
        st.warning(f"No data available for {company}")
        return
    
    # Get latest period data
    latest_period = company_data['period_date'].max()
    latest_data = company_data[company_data['period_date'] == latest_period]
    
    # Display key metrics in columns
    cols = st.columns(4)
    
    key_metrics = ['Revenue', 'EBITDA', 'Net Income', 'EPS']
    
    for idx, metric in enumerate(key_metrics):
        metric_data = latest_data[latest_data['kpi_label'].str.contains(metric, case=False)]
        if not metric_data.empty:
            value = metric_data.iloc[0]['value']
            yoy_growth = metric_data.iloc[0].get('yoy_growth', 0)
            
            with cols[idx % 4]:
                st.metric(
                    label=metric,
                    value=f"{value:,.0f}",
                    delta=f"{yoy_growth:.1f}%" if yoy_growth else None
                )

def main():
    st.title("📊 KPI Dashboard")
    
    # Last update info
    st.sidebar.markdown("### 🔄 Data Status")
    
    # Check for last update
    try:
        metadata_path = Path('data/csv/metadata.json')
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                last_update = metadata.get('refresh_timestamp', 'Unknown')
                st.sidebar.info(f"Last updated: {last_update}")
    except:
        st.sidebar.warning("Update status unknown")
    
    # Manual refresh button (triggers GitHub Action)
    if st.sidebar.button("🔄 Trigger Refresh"):
        st.info("To trigger a manual refresh, go to GitHub Actions and run the workflow")
        st.markdown("[Go to GitHub Actions](https://github.com/YOUR_USERNAME/YOUR_REPO/actions)")
    
    # Load data
    df, metadata = load_data()
    
    if df is None:
        st.stop()
    
    # Sidebar filters
    st.sidebar.markdown("### 📊 Filters")
    
    # Company filter
    all_companies = sorted(df['ticker'].unique())
    selected_companies = st.sidebar.multiselect(
        "Select Companies",
        all_companies,
        default=all_companies[:3] if len(all_companies) > 3 else all_companies
    )
    
    # KPI category filter
    all_categories = sorted(df['category'].unique())
    selected_categories = st.sidebar.multiselect(
        "Select Categories",
        all_categories,
        default=all_categories
    )
    
    # Time period filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(df['period_date'].min(), df['period_date'].max()),
        min_value=df['period_date'].min(),
        max_value=df['period_date'].max()
    )
    
    # Filter data
    filtered_df = df[
        (df['ticker'].isin(selected_companies)) &
        (df['category'].isin(selected_categories)) &
        (df['period_date'] >= pd.to_datetime(date_range[0])) &
        (df['period_date'] <= pd.to_datetime(date_range[1]))
    ]
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🏢 Company View", "📊 KPI Analysis", "📋 Raw Data"])
    
    with tab1:
        st.header("Performance Overview")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Companies", len(selected_companies))
        with col2:
            st.metric("KPIs Tracked", filtered_df['kpi_label'].nunique())
        with col3:
            st.metric("Data Points", len(filtered_df))
        with col4:
            st.metric("Time Periods", filtered_df['period_name'].nunique())
        
        # Top KPIs by company
        st.subheader("Key Metrics by Company")
        for company in selected_companies:
            with st.expander(f"{company} - Latest Metrics", expanded=True):
                display_company_metrics(filtered_df, company)
    
    with tab2:
        st.header("Company Deep Dive")
        
        selected_company = st.selectbox("Select Company", selected_companies)
        
        if selected_company:
            company_df = filtered_df[filtered_df['ticker'] == selected_company]
            
            # KPI selection for charting
            available_kpis = sorted(company_df['kpi_label'].unique())
            selected_kpi = st.selectbox("Select KPI to visualize", available_kpis)
            
            if selected_kpi:
                # Time series chart
                kpi_data = company_df[company_df['kpi_label'] == selected_kpi].sort_values('period_date')
                
                fig = go.Figure()
                
                # Add actual values
                fig.add_trace(go.Scatter(
                    x=kpi_data['period_date'],
                    y=kpi_data['value'],
                    mode='lines+markers',
                    name='Actual',
                    line=dict(color='blue', width=2)
                ))
                
                # Add forecast values if available
                forecast_data = kpi_data[kpi_data['is_forecast'] == True]
                if not forecast_data.empty:
                    fig.add_trace(go.Scatter(
                        x=forecast_data['period_date'],
                        y=forecast_data['value'],
                        mode='lines+markers',
                        name='Forecast',
                        line=dict(color='orange', dash='dash')
                    ))
                
                fig.update_layout(
                    title=f"{selected_kpi} - {selected_company}",
                    xaxis_title="Period",
                    yaxis_title=kpi_data.iloc[0]['units'] if not kpi_data.empty else "Value",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Growth metrics
                col1, col2 = st.columns(2)
                with col1:
                    if 'qoq_growth' in kpi_data.columns:
                        latest_qoq = kpi_data.iloc[-1]['qoq_growth']
                        st.metric("Latest QoQ Growth", f"{latest_qoq:.1f}%" if pd.notna(latest_qoq) else "N/A")
                
                with col2:
                    if 'yoy_growth' in kpi_data.columns:
                        latest_yoy = kpi_data.iloc[-1]['yoy_growth']
                        st.metric("Latest YoY Growth", f"{latest_yoy:.1f}%" if pd.notna(latest_yoy) else "N/A")
    
    with tab3:
        st.header("KPI Comparison")
        
        # Select KPI for comparison
        all_kpis = sorted(filtered_df['kpi_label'].unique())
        selected_kpi_compare = st.selectbox("Select KPI to compare", all_kpis, key="compare")
        
        if selected_kpi_compare:
            # Create comparison chart
            fig = create_kpi_chart(filtered_df, selected_kpi_compare, selected_companies)
            st.plotly_chart(fig, use_container_width=True)
            
            # Comparison table
            st.subheader("Latest Values Comparison")
            comparison_data = []
            
            for company in selected_companies:
                company_kpi = filtered_df[
                    (filtered_df['ticker'] == company) & 
                    (filtered_df['kpi_label'] == selected_kpi_compare)
                ]
                
                if not company_kpi.empty:
                    latest = company_kpi.loc[company_kpi['period_date'].idxmax()]
                    comparison_data.append({
                        'Company': company,
                        'Latest Value': f"{latest['value']:,.0f}",
                        'Period': latest['period_name'],
                        'YoY Growth': f"{latest.get('yoy_growth', 0):.1f}%"
                    })
            
            if comparison_data:
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, use_container_width=True)
    
    with tab4:
        st.header("Raw Data Explorer")
        
        # Display options
        col1, col2 = st.columns(2)
        with col1:
            show_forecast = st.checkbox("Include Forecast Data", value=True)
        with col2:
            show_growth = st.checkbox("Show Growth Metrics", value=True)
        
        # Filter based on options
        display_df = filtered_df.copy()
        if not show_forecast:
            display_df = display_df[display_df['is_forecast'] == False]
        
        # Select columns to display
        base_columns = ['ticker', 'company_name', 'period_name', 'period_date', 
                       'kpi_label', 'value', 'units', 'category']
        
        if show_growth:
            growth_columns = ['qoq_growth', 'yoy_growth']
            display_columns = base_columns + growth_columns
        else:
            display_columns = base_columns
        
        # Display filtered data
        st.dataframe(
            display_df[display_columns].sort_values(['ticker', 'kpi_label', 'period_date']),
            use_container_width=True
        )
        
        # Download button
        csv = display_df[display_columns].to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data",
            data=csv,
            file_name=f"kpi_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()