"""
Daily Scheduler for Canalyst KPI Retrieval
Runs the retrieval script automatically at specified times
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_kpi_retrieval():
    """Execute the KPI retrieval script"""
    logging.info("Starting scheduled KPI retrieval...")
    
    try:
        # Run the main script
        result = subprocess.run(
            [sys.executable, 'canalyst_python_solution.py'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logging.info("KPI retrieval completed successfully")
            logging.info(f"Output: {result.stdout[-500:]}")  # Last 500 chars
        else:
            logging.error(f"KPI retrieval failed with code {result.returncode}")
            logging.error(f"Error: {result.stderr}")
            
    except Exception as e:
        logging.error(f"Error running KPI retrieval: {str(e)}")

def run_once_now():
    """Run the retrieval once for testing"""
    print("Running KPI retrieval now...")
    run_kpi_retrieval()
    print("Done! Check the exports folder for results.")

def main():
    """Set up and run the scheduler"""
    print("\n📅 Canalyst KPI Retrieval Scheduler")
    print("=" * 50)
    
    # Schedule options
    print("\nSchedule options:")
    print("1. Run once now (for testing)")
    print("2. Run daily at 6:00 AM")
    print("3. Run every hour (for testing)")
    print("4. Custom schedule")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        run_once_now()
        return
    
    elif choice == '2':
        schedule.every().day.at("06:00").do(run_kpi_retrieval)
        print("✅ Scheduled for daily runs at 6:00 AM")
        
    elif choice == '3':
        schedule.every().hour.do(run_kpi_retrieval)
        print("✅ Scheduled for hourly runs")
        
    elif choice == '4':
        time_str = input("Enter time (HH:MM format, e.g., 14:30): ").strip()
        try:
            schedule.every().day.at(time_str).do(run_kpi_retrieval)
            print(f"✅ Scheduled for daily runs at {time_str}")
        except:
            print("❌ Invalid time format")
            return
    
    else:
        print("❌ Invalid choice")
        return
    
    print("\n🏃 Scheduler is running...")
    print("Press Ctrl+C to stop\n")
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Scheduler stopped by user")
        logging.info("Scheduler stopped by user")

if __name__ == "__main__":
    main()