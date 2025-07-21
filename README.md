# Auto-Financials KPI Refresh System

A Streamlit-based dashboard for exploring financial KPIs from the Canalyst/Tegus API.

## Features

- **Single Company Mode**: Search and explore KPIs for individual companies
- **Multi-Company Mode**: Compare metrics across multiple companies
- **Metric Grouping**: Create custom groups to compare similar metrics with different names across companies
- **Interactive Charts**: Line and bar charts with Plotly
- **Data Export**: Download data in CSV or Excel format
- **Smart Formatting**: Automatic number formatting (millions, percentages)

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure API credentials:
   - Copy `config/config_example.yaml` to `config/config.yaml`
   - Add your Canalyst API key

4. Run the Streamlit app:
   ```bash
   cd kpi_refresh_system
   streamlit run streamlit_app.py
   ```

## Usage

### Single Company Mode
1. Enter a ticker symbol (e.g., ANF, VSCO)
2. Select KPIs from the discovered metrics
3. Choose time period and view data/charts

### Multi-Company Mode
1. Toggle "Multi-Company Comparison"
2. Search and select metrics for each company
3. Create metric groups to compare similar metrics
4. Use checkboxes to combine multiple metrics (they'll be summed)
5. View data in "By Metric" or "By Company" format

## File Structure

- `kpi_refresh_system/streamlit_app.py` - Main Streamlit application
- `kpi_refresh_system/src/` - Core modules (API client, data processor, etc.)
- `config/` - Configuration files and mappings
- `main.py` - CLI tool for batch processing