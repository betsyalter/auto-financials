# API Key Setup Guide

## Option 1: Local Development (Desktop)

Run one of these scripts:
```bash
# Secure method (hides input)
python setup_api_key.py

# Quick method (shows input)
python quick_setup.py
```

## Option 2: Manual Setup

Create a file named `.env` in the `kpi_refresh_system` folder with:
```
CANALYST_API_TOKEN=your_actual_api_token_here
```

## Option 3: Streamlit Cloud Deployment

1. Go to your Streamlit app dashboard
2. Click on your app settings (⋮ menu)
3. Go to "Secrets"
4. Add:
   ```toml
   CANALYST_API_TOKEN = "your_actual_api_token_here"
   ```

## Option 4: Running from Phone/Tablet

Since you can't easily create files on mobile:

1. **Use Streamlit Cloud** (recommended)
   - Deploy the app to Streamlit Cloud
   - Set the API key in Streamlit secrets (see Option 3)
   - Access via browser on any device

2. **Use GitHub Codespaces**
   - Open your repo in GitHub Codespaces
   - Run `python quick_setup.py` in the terminal
   - Enter your API key when prompted

## Option 5: Environment Variable (Command Line)

On Windows:
```cmd
set CANALYST_API_TOKEN=your_token_here
python main.py refresh
```

On Mac/Linux:
```bash
export CANALYST_API_TOKEN=your_token_here
python main.py refresh
```

## Security Notes

- Never commit your API key to git
- The `.env` file is gitignored (safe)
- Each user needs their own API key
- For production, use Streamlit secrets or environment variables