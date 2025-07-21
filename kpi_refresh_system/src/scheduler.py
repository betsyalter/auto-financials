import schedule
import time
from datetime import datetime
from loguru import logger
import pytz

class KPIScheduler:
    def __init__(self, refresh_function, config):
        self.refresh_function = refresh_function
        self.config = config
        self.timezone = pytz.timezone(config.get('scheduling', {}).get('timezone', 'US/Pacific'))
        
    def run_refresh(self):
        """Execute the refresh function with error handling"""
        try:
            logger.info("Starting scheduled KPI refresh")
            start_time = datetime.now()
            
            self.refresh_function()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Scheduled refresh completed in {duration:.1f} seconds")
            
        except Exception as e:
            logger.error(f"Scheduled refresh failed: {str(e)}")
            # Could add email/slack notification here
    
    def start(self):
        """Start the scheduler"""
        # Get schedule time from config
        schedule_time = self.config.get('scheduling', {}).get('time', '06:00')
        
        # Schedule daily run
        schedule.every().day.at(schedule_time).do(self.run_refresh)
        
        logger.info(f"Scheduler started. Will run daily at {schedule_time} PT")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
    
    def run_once(self):
        """Run refresh once immediately"""
        self.run_refresh()