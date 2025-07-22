import streamlit as st
import pandas as pd
from src.canalyst_client import CanalystClient
from src.config import load_config
import json
from src.utils.paths import resolve_path
from pathlib import Path

st.set_page_config(page_title="KPI Selector", layout="wide")

@st.cache_resource
def get_client():
    config = load_config()
    return CanalystClient(config)

@st.cache_data
def load_company_mappings():
    # Try direct path first (for deployment), then resolve_path
    mappings_path = Path('config/company_mappings.csv')
    if not mappings_path.exists():
        mappings_path = resolve_path('kpi_refresh_system', 'config', 'company_mappings.csv')
    return pd.read_csv(mappings_path)

@st.cache_data
def get_company_kpis(csin: str):
    client = get_client()
    model = client.get_latest_equity_model(csin)
    model_version = model['model_version']['name']
    
    # Get all time series
    all_ts = client.list_time_series(csin, model_version)
    
    # Separate KPIs and non-KPIs
    kpis = [ts for ts in all_ts if ts.get('kpi_data', {}).get('is_kpi', False)]
    other = [ts for ts in all_ts if not ts.get('kpi_data', {}).get('is_kpi', False)]
    
    return kpis, other, model

def main():
    st.title("📊 Canalyst KPI Selector")
    
    # Load companies
    companies = load_company_mappings()
    
    # Sidebar for company selection
    with st.sidebar:
        st.header("Company Selection")
        
        selected_ticker = st.selectbox(
            "Select Company",
            companies['search_ticker'].tolist(),
            format_func=lambda x: f"{x} - {companies[companies['search_ticker']==x]['name'].iloc[0]}"
        )
        
        company_row = companies[companies['search_ticker'] == selected_ticker].iloc[0]
        csin = company_row['csin']
        
        st.info(f"**CSIN:** {csin}\n\n**Sector:** {company_row.get('sector', 'N/A')}")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(f"KPIs for {selected_ticker}")
        
        # Load KPIs
        with st.spinner("Loading KPIs..."):
            kpis, other_ts, model = get_company_kpis(csin)
        
        st.success(f"Found {len(kpis)} KPIs in model {model['model_version']['name']}")
        
        # Category filter
        categories = sorted(set(kpi['category']['description'] for kpi in kpis))
        selected_categories = st.multiselect(
            "Filter by Category",
            categories,
            default=categories[:3] if len(categories) > 3 else categories
        )
        
        # Search
        search_term = st.text_input("Search KPIs", placeholder="Enter keyword...")
        
        # Filter KPIs
        filtered_kpis = kpis
        
        if selected_categories:
            filtered_kpis = [k for k in filtered_kpis 
                           if k['category']['description'] in selected_categories]
        
        if search_term:
            search_lower = search_term.lower()
            filtered_kpis = [k for k in filtered_kpis
                           if search_lower in k['description'].lower() or
                           any(search_lower in name.lower() for name in k['names'])]
        
        st.info(f"Showing {len(filtered_kpis)} KPIs")
        
        # Display KPIs grouped by category
        if 'selected_kpis' not in st.session_state:
            st.session_state.selected_kpis = {}
        
        if csin not in st.session_state.selected_kpis:
            st.session_state.selected_kpis[csin] = []
        
        # Group by category
        kpis_by_category = {}
        for kpi in filtered_kpis:
            cat = kpi['category']['description']
            if cat not in kpis_by_category:
                kpis_by_category[cat] = []
            kpis_by_category[cat].append(kpi)
        
        # Display each category
        for category, cat_kpis in sorted(kpis_by_category.items()):
            with st.expander(f"**{category}** ({len(cat_kpis)} KPIs)", expanded=True):
                
                # Select all in category
                col_all, col_clear = st.columns(2)
                with col_all:
                    if st.button(f"Select All", key=f"all_{category}"):
                        for kpi in cat_kpis:
                            if kpi['slug'] not in [k['slug'] for k in st.session_state.selected_kpis[csin]]:
                                st.session_state.selected_kpis[csin].append(kpi)
                        st.rerun()
                
                with col_clear:
                    if st.button(f"Clear All", key=f"clear_{category}"):
                        st.session_state.selected_kpis[csin] = [
                            k for k in st.session_state.selected_kpis[csin]
                            if k['category']['description'] != category
                        ]
                        st.rerun()
                
                # Display KPIs
                for kpi in sorted(cat_kpis, key=lambda x: x['names'][0]):
                    is_selected = kpi['slug'] in [k['slug'] for k in st.session_state.selected_kpis[csin]]
                    
                    col_check, col_name, col_desc = st.columns([1, 3, 6])
                    
                    with col_check:
                        if st.checkbox("", value=is_selected, key=f"kpi_{kpi['slug']}"):
                            if not is_selected:
                                st.session_state.selected_kpis[csin].append(kpi)
                            else:
                                st.session_state.selected_kpis[csin] = [
                                    k for k in st.session_state.selected_kpis[csin]
                                    if k['slug'] != kpi['slug']
                                ]
                            st.rerun()
                    
                    with col_name:
                        st.text(kpi['names'][0])
                    
                    with col_desc:
                        st.caption(f"{kpi['description']} ({kpi['unit']['description']})")
                        if len(kpi['names']) > 1:
                            with st.expander("Alt names"):
                                st.text(", ".join(kpi['names'][1:]))
    
    with col2:
        st.header("Selected KPIs")
        
        selected_count = len(st.session_state.selected_kpis.get(csin, []))
        st.metric("Total Selected", selected_count)
        
        if selected_count > 0:
            # Group selected by category
            selected_by_cat = {}
            for kpi in st.session_state.selected_kpis[csin]:
                cat = kpi['category']['description']
                if cat not in selected_by_cat:
                    selected_by_cat[cat] = []
                selected_by_cat[cat].append(kpi)
            
            # Display selected
            for cat, kpis in sorted(selected_by_cat.items()):
                st.subheader(f"{cat} ({len(kpis)})")
                for kpi in kpis:
                    with st.container():
                        col_del, col_info = st.columns([1, 9])
                        with col_del:
                            if st.button("🗑️", key=f"del_{kpi['slug']}"):
                                st.session_state.selected_kpis[csin] = [
                                    k for k in st.session_state.selected_kpis[csin]
                                    if k['slug'] != kpi['slug']
                                ]
                                st.rerun()
                        with col_info:
                            st.text(kpi['names'][0])
                            st.caption(kpi['description'])
            
            st.divider()
            
            # Export options
            if st.button("💾 Export Selections", type="primary"):
                # Prepare export data
                export_rows = []
                for kpi in st.session_state.selected_kpis[csin]:
                    export_rows.append({
                        'csin': csin,
                        'ticker': selected_ticker,
                        'time_series_name': kpi['names'][0],
                        'time_series_slug': kpi['slug'],
                        'kpi_label': kpi['description'],
                        'units': kpi['unit']['description'],
                        'category': kpi['category']['description'],
                        'all_names': '|'.join(kpi['names'])
                    })
                
                df = pd.DataFrame(export_rows)
                
                # Download buttons
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"kpi_selections_{selected_ticker}.csv",
                    mime="text/csv"
                )
                
                json_str = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="Download as JSON",
                    data=json_str,
                    file_name=f"kpi_selections_{selected_ticker}.json",
                    mime="application/json"
                )

if __name__ == "__main__":
    main()