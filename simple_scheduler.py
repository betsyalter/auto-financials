"""
Simple Scheduler for KPI Retrieval
Run this script to schedule automatic daily updates
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime
import os

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
            ['python', 'kpi_retrieval_no_vba.py'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logging.info("KPI retrieval completed successfully")
        else:
            logging.error(f"KPI retrieval failed: {result.stderr}")
            
    except Exception as e:
        logging.error(f"Error running KPI retrieval: {str(e)}")

def main():
    """Set up and run the scheduler"""
    # Schedule daily run at 6:00 AM
    schedule.every().day.at("06:00").do(run_kpi_retrieval)
    
    logging.info("Scheduler started. Daily runs scheduled for 6:00 AM")
    logging.info("Press Ctrl+C to stop")
    
    # Run once immediately for testing
    if input("Run once now for testing? (y/n): ").lower() == 'y':
        run_kpi_retrieval()
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")

if __name__ == "__main__":
    main()