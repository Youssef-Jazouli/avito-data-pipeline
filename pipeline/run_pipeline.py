import logging
import os
import sys
import time
import traceback

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/pipeline.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Also log to stdout so docker-compose logs captures it
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
logging.getLogger().addHandler(console)

def run_step(name, func, retries=3):
    for attempt in range(1, retries + 1):
        try:
            logging.info(f"[{name}] Starting (attempt {attempt})")
            func()
            logging.info(f"[{name}] Done.")
            return True
        except Exception as e:
            logging.error(f"[{name}] Failed attempt {attempt}: {e}")
            traceback.print_exc()
            if attempt < retries:
                time.sleep(5)
    logging.critical(f"[{name}] All {retries} attempts failed. Stopping pipeline.")
    return False

def main():
    sys.path.insert(0, "/app")

    try:
        from scraper.scraper import main as scrape
        from staging.load_staging import load as stage
        from clean.clean_data import clean
        from warehouse.load_warehouse import load as warehouse
    except Exception as e:
        print(f"IMPORT ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

    steps = [
        ("Scraping", scrape),
        ("Staging", stage),
        ("Cleaning", clean),
        ("Warehouse", warehouse),
    ]

    for name, func in steps:
        if not run_step(name, func):
            sys.exit(1)

    logging.info("Pipeline completed successfully.")
    print("Pipeline completed successfully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}")
        traceback.print_exc()
        sys.exit(1)