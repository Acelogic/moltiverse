#!/usr/bin/env python3
"""
Molt Discovery Pipeline
1. Runs the crawler to find new sites
2. Syncs discoveries to portals.json

Usage:
  python3 discover.py           # Full crawl + sync
  python3 discover.py --sync    # Just sync (skip crawl)
  python3 discover.py --fast    # Fast crawl (less brute force)
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from crawler import Database, Crawler, SEED_URLS
from sync_portals import sync


async def run_crawler(fast_mode: bool = False):
    """Run the crawler."""
    db = Database()
    crawler = Crawler(db)
    await crawler.run()
    return len(crawler.discoveries)


def main():
    args = sys.argv[1:]

    # Just sync mode
    if '--sync' in args:
        print("📋 Sync-only mode\n")
        sync()
        return

    # Fast mode - less brute force
    fast = '--fast' in args

    print("🦞 MOLT DISCOVERY PIPELINE")
    print("=" * 50)

    # Run crawler
    print("\n📡 STEP 1: CRAWLING FOR NEW SITES")
    print("-" * 40)
    new_sites = asyncio.run(run_crawler(fast_mode=fast))

    # Sync to portals.json
    print("\n📋 STEP 2: SYNCING TO PORTALS.JSON")
    print("-" * 40)
    sync()

    print("\n" + "=" * 50)
    print("✅ DISCOVERY COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
