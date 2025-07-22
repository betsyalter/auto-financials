"""
KPI Dashboard - Multi-page Streamlit App
"""
import streamlit as st

st.set_page_config(
    page_title="KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 KPI Dashboard")
st.markdown("### Financial Metrics Analysis Tool")

st.info("""
👈 Use the sidebar to navigate between pages:
- **Select Tickers**: Configure companies and metrics to analyze
- **By Metric**: Compare metrics across multiple companies
- **By Company**: Analyze all metrics for a single company
""")

# Add some helpful context
with st.expander("ℹ️ About this Dashboard"):
    st.markdown("""
    This dashboard allows you to:
    - Fetch and analyze financial KPIs from multiple companies
    - Compare metrics across companies or view all metrics for a single company
    - Export data to Excel for further analysis
    - Visualize trends with interactive charts
    
    Start by selecting tickers in the sidebar navigation.
    """)

st.sidebar.success("👆 Select a page above")