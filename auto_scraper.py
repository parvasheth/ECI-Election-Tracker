import time
import subprocess
import datetime
import sys

def main():
    print("="*50)
    print("🚀 ECI Election Live Scraper - Local Automation 🚀")
    print("="*50)
    print("This script will automatically run the scraper every 15 minutes.")
    print("Just leave this terminal open and your laptop awake.")
    print("Press [Ctrl+C] at any time to stop the automation.\n")
    
    interval_seconds = 15 * 60  # 15 minutes
    
    while True:
        now = datetime.datetime.now()
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Executing scraper pipeline...")
        
        try:
            # Execute the scraper.py script
            # We use sys.executable to ensure we use the same python interpreter
            subprocess.run([sys.executable, "scraper.py"], check=True)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Scrape completed and Google Sheet updated.")
        except subprocess.CalledProcessError as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ Scraper failed with error code: {e.returncode}")
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ An unexpected error occurred: {e}")
            
        print(f"\n⏳ Waiting for 15 minutes before the next run...")
        print(f"Next update scheduled at: {(now + datetime.timedelta(seconds=interval_seconds)).strftime('%H:%M:%S')}\n")
        
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n🛑 Automation stopped by user. Exiting...")
            break

if __name__ == "__main__":
    main()
