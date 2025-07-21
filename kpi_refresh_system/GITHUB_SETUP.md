# GitHub Actions Setup for KPI Refresh

## 🚀 Quick Setup Guide

### 1. Push Code to GitHub
```bash
git init
git add .
git commit -m "Initial KPI refresh system"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/kpi-refresh-system.git
git push -u origin main
```

### 2. Add GitHub Secret
1. Go to your repository on GitHub
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add:
   - Name: `CANALYST_API_TOKEN`
   - Value: Your Canalyst API token

### 3. Enable GitHub Actions
1. Go to **Actions** tab in your repository
2. You should see "Daily KPI Refresh" workflow
3. Click on it and enable if needed

### 4. Test Manual Run
1. Go to **Actions** tab
2. Click on "Daily KPI Refresh" workflow
3. Click **Run workflow** → **Run workflow**
4. Watch the execution

## 📊 Streamlit Dashboard Deployment

### Option 1: Streamlit Community Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Deploy `streamlit_kpi_dashboard.py`
4. Add secrets in Streamlit:
   ```toml
   # .streamlit/secrets.toml
   CANALYST_API_TOKEN = "your-token-here"
   ```

### Option 2: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run streamlit_kpi_dashboard.py

# Run the KPI selector
streamlit run streamlit_kpi_selector.py
```

## 🔄 Workflow Overview

1. **Daily at 6am PT**: GitHub Actions runs `python main.py refresh`
2. **Data Processing**: Fetches from Canalyst API, processes KPIs
3. **Commit Results**: Saves Excel and CSV files back to repository
4. **Streamlit Updates**: Dashboard automatically shows latest data

## 📁 Data Flow

```
GitHub Actions (6am PT)
    ↓
Canalyst API
    ↓
Python Processing
    ↓
Git Commit (data/csv/, data/output/)
    ↓
Streamlit Dashboard (reads from repo)
```

## 🛠️ Customization

### Change Schedule
Edit `.github/workflows/daily-kpi-refresh.yml`:
```yaml
- cron: '0 14 * * *'  # 6am PT (2pm UTC)
```

### Add Manual Trigger in Streamlit
You can trigger GitHub Actions via API:
```python
import requests

def trigger_refresh():
    headers = {
        'Authorization': f'token {st.secrets["GITHUB_TOKEN"]}',
        'Accept': 'application/vnd.github.v3+json',
    }
    
    response = requests.post(
        f'https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/actions/workflows/daily-kpi-refresh.yml/dispatches',
        headers=headers,
        json={'ref': 'main'}
    )
```

## 📈 Benefits

1. **Automated**: Runs daily without intervention
2. **Version Controlled**: All data changes tracked in Git
3. **Free**: GitHub Actions provides 2000 minutes/month free
4. **Reliable**: GitHub's infrastructure ensures uptime
5. **Transparent**: See all refresh logs and history

## 🔍 Monitoring

- Check run history: `Actions` tab → `Daily KPI Refresh`
- View logs: Click on any workflow run
- Download artifacts: Available for 30 days per run
- Email notifications: GitHub sends emails on failures

## 🚨 Troubleshooting

1. **Workflow not running**: Check if Actions are enabled
2. **API errors**: Verify `CANALYST_API_TOKEN` secret
3. **No data updates**: Check git commit logs
4. **Streamlit not updating**: Clear cache with `c` key