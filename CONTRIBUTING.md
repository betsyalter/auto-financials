# Contributing Guidelines

## Branch Protection Notice
The `main` branch is protected. You cannot push directly to it. Please follow these steps to make changes:

## Setup Instructions

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/betsyalter/auto-financials.git
   cd auto-financials
   ```

2. **Create a new branch** for your changes:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```
   
   Use descriptive branch names like:
   - `feature/add-export-functionality`
   - `fix/data-processing-error`
   - `refactor/improve-api-calls`

## Making Changes

1. **Make your changes** on your feature branch
2. **Commit regularly** with clear messages:
   ```bash
   git add .
   git commit -m "feat: Add new export format for quarterly data"
   ```

3. **Push your branch** to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```

## Creating a Pull Request

1. Go to https://github.com/betsyalter/auto-financials
2. Click "Pull requests" → "New pull request"
3. Select your branch as the source
4. Add a clear title and description explaining:
   - What changes you made
   - Why you made them
   - Any testing you did
5. Create the pull request

## Important Notes

- **DO NOT** attempt to push directly to `main` - it will be rejected
- **DO NOT** use `--force` on shared branches
- **TEST** your changes locally before creating a PR
- The Streamlit app auto-deploys from `main`, so only tested code should be merged

## Working with the KPI Refresh System

### Local Development Setup
```bash
cd kpi_refresh_system
pip install -r requirements.txt
cp .env.example .env  # Add your API credentials
```

### Testing Locally
```bash
# Test the Streamlit app
streamlit run streamlit_app.py

# Test CLI commands
python main.py list
python main.py refresh
```

### Key Files
- `streamlit_app.py` - Main Streamlit application
- `src/canalyst_client.py` - API client
- `src/data_processor.py` - Data processing logic
- `config/config.yaml` - Configuration settings

## Need Help?

If you need to make urgent changes to `main` while Betsy is away:
1. Create your PR as usual
2. Contact another team member with repository access to review and merge
3. Or wait for Betsy to return and review

Remember: The branch protection is there to prevent accidental deployments of untested code to the live Streamlit app.