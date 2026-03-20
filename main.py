# ============================================================
# main.py — entry point: ties everything together, runs the scheduler
# ============================================================

import schedule
import time
from scraper import scrape_all
from storage import save_prices, load_latest_prices
from alerts  import check_for_drops
from config  import SEARCH_QUERIES, CHECK_INTERVAL_HOURS


def run() -> None:
    """One full cycle: scrape → compare → alert → save."""
    print("\n[main] Starting scrape cycle...")

    current  = scrape_all(SEARCH_QUERIES)           # 1. fetch latest prices from Newegg
    previous = load_latest_prices()                 # 2. load last saved prices from DB

    if previous:                                    # 3. only compare if we have a baseline
        check_for_drops(previous, current)
    else:
        print("[main] First run — no previous prices to compare yet, just saving baseline.")

    save_prices(current)                            # 4. persist this run to the database
    print(f"[main] Cycle complete. Next check in {CHECK_INTERVAL_HOURS} hour(s).\n")


if __name__ == "__main__":
    run()                                           # always run once immediately on start

    schedule.every(CHECK_INTERVAL_HOURS).hours.do(run)  # then repeat on the interval

    while True:
        schedule.run_pending()                      # check if any scheduled job is due
        time.sleep(60)                              # sleep 60s between checks (low CPU usage)
