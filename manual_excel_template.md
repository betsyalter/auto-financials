# Manual Excel Template for KPI Tracking

If you prefer to work without any programming, here's a simple manual process:

## Step 1: Create Excel Template

### Sheet 1: KPI_Data
Create columns:
- A: Ticker (AAPL_US, MSFT_US, etc.)
- B: KPI Name (Revenue, Gross Profit, etc.)
- C-G: FY24, FY23, FY22, FY21, FY20
- H-S: Q1-25, Q4-24, Q3-24, Q2-24, Q1-24, Q4-23, Q3-23, Q2-23, Q1-23, Q4-22, Q3-22, Q2-22

### Sheet 2: Growth_Calculations
Use Excel formulas:
- YoY Growth: =(C2-D2)/D2
- QoQ Growth: =(H2-I2)/I2

## Step 2: Manual Data Entry Process

1. **Open Tegus/Canalyst Excel Add-in**
2. **For each ticker and KPI:**
   - Use the TEGUS.CD formula
   - Copy values to your template
   - Example: =TEGUS.CD("AAPL_US", "MO_RIS_REV", "FY24")

3. **Export to CSV:**
   - File → Save As → CSV (UTF-8)

## Step 3: Use Power Query (Built into Excel)

Power Query can automate some of this:

1. **Data → Get Data → From Folder**
   - Point to folder with CSV files
   - Combine and transform data

2. **Transform Data:**
   - Unpivot columns for long format
   - Add calculated columns for growth

3. **Refresh:**
   - Right-click query → Refresh

This gives you automation without VBA!