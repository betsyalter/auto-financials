# KPI Refresh System

A comprehensive Python-based system for automated financial KPI tracking using the Canalyst API.

## 🚀 Features

- **CSIN Discovery**: Find Canalyst Security Identification Numbers for any company
- **KPI Discovery**: Browse and select from thousands of available KPIs
- **Automated Refresh**: Daily scheduled data updates via GitHub Actions
- **Multiple Export Formats**: Excel for business users, CSV/JSON for dashboards
- **Streamlit Integration**: Web-based interfaces for discovery and visualization
- **Growth Calculations**: Automatic QoQ and YoY calculations

## 📋 Prerequisites

- Python 3.11+
- Canalyst API Token
- Git (for version control)
- GitHub account (for automated scheduling)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd kpi_refresh_system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key securely**
   ```bash
   # Run the secure setup script
   python setup_api_key.py
   ```
   
   This will prompt you for your Canalyst API token and store it securely in a `.env` file that is NOT tracked by git.
   
   **⚠️ Security Note**: Never commit your API key to git. Each team member must run this setup locally.

## 🔧 Configuration

### Step 1: Discover CSINs

Find Canalyst identifiers for your companies:

```bash
# Interactive mode
python main.py discover-csin

# Find single company
python main.py find-csin AAPL

# Bulk search from file
python main.py bulk-find-csin example_tickers.txt
```

### Step 2: Select KPIs

Choose which metrics to track:

```bash
# CLI interactive mode
python main.py discover-kpis AAPL

# Web interface
streamlit run streamlit_kpi_selector.py
```

### Step 3: Configure Mappings

The system uses two configuration files:
- `config/company_mappings.csv`: Maps tickers to CSINs
- `config/kpi_mappings.csv`: Defines which KPIs to track per company

## 📊 Usage

### Manual Refresh

```bash
# Refresh all companies
python main.py refresh

# Refresh specific companies
python main.py refresh -t AAPL -t MSFT

# Test single company
python main.py test-ticker AAPL
```

### Scheduled Refresh

```bash
# Run local scheduler (6am PT daily)
python main.py schedule
```

### View Data

```bash
# Launch dashboard
streamlit run streamlit_kpi_dashboard.py
```

## 🚀 GitHub Actions Deployment

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Add Secret**
   - Go to Settings → Secrets → Actions
   - Add `CANALYST_API_TOKEN`

3. **Enable Actions**
   - Go to Actions tab
   - Enable the workflow

## 📁 Project Structure

```
kpi_refresh_system/
├── config/
│   ├── config.yaml              # API and system settings
│   ├── company_mappings.csv     # Ticker to CSIN mappings
│   └── kpi_mappings.csv         # KPI selections
├── src/
│   ├── canalyst_client.py       # API client
│   ├── data_processor.py        # Data transformation
│   ├── excel_manager.py         # Excel export
│   ├── csv_exporter.py          # CSV export
│   ├── scheduler.py             # Task scheduling
│   └── config.py                # Configuration loader
├── data/
│   ├── output/                  # Excel files
│   └── csv/                     # CSV exports
├── tests/                       # Unit tests
├── .github/workflows/           # GitHub Actions
├── main.py                      # CLI interface
├── csin_discovery.py            # CSIN lookup tool
├── kpi_discovery.py             # KPI selection tool
├── streamlit_kpi_selector.py    # Web KPI selector
└── streamlit_kpi_dashboard.py   # Web dashboard
```

## 🔍 CLI Commands

| Command | Description |
|---------|-------------|
| `refresh` | Run KPI refresh for all/specific companies |
| `schedule` | Start scheduled daily refresh |
| `test-ticker` | Test API connection with single ticker |
| `list-companies` | Show configured companies |
| `discover-csin` | Interactive CSIN discovery |
| `find-csin` | Find CSIN for specific ticker |
| `bulk-find-csin` | Bulk CSIN lookup from file |
| `discover-kpis` | Interactive KPI selection |
| `list-kpis` | List available KPIs for a company |
| `explore-taxonomy` | Browse Canalyst metrics taxonomy |

## 📈 Output Formats

### Excel (`data/output/`)
- Formatted workbook with company sheets
- Summary dashboard
- Growth calculations
- Conditional formatting

### CSV (`data/csv/`)
- Long-format data for analysis
- Metadata JSON file
- Streamlit-compatible structure

## 🐛 Troubleshooting

### API Connection Issues
```bash
# Test API connection
python -c "from src.canalyst_client import CanalystClient; from src.config import load_config; client = CanalystClient(load_config()); print('Connected!')"
```

### Missing Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### CSIN Not Found
- Try different ticker types (Bloomberg, CapIQ, etc.)
- Check if company is in Canalyst coverage
- Use company name search instead

## 📝 License

This project is proprietary and confidential.

## 🤝 Support

For issues or questions:
- Check the logs in `logs/` directory
- Review GitHub Actions logs for scheduled runs
- Contact Canalyst support for API issues