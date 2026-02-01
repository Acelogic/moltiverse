#!/usr/bin/env python3
"""
Molt Discovery Pipeline
1. Runs the crawler to find new sites
2. Syncs discoveries to portals.json
3. Optionally verifies sites with LLM

Usage:
  python3 discover.py              # Full crawl + sync
  python3 discover.py --sync       # Just sync (skip crawl)
  python3 discover.py --fast       # Fast crawl (less brute force)
  python3 discover.py --verify     # Also run LLM verification
  python3 discover.py --dedup      # Check for duplicates in portals.json
"""

import asyncio
import sys
import json
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from crawler import Database, Crawler, SEED_URLS
from sync_portals import sync

PORTALS_JSON = Path(__file__).parent.parent / "portals.json"


async def run_crawler(fast_mode: bool = False):
    """Run the crawler."""
    db = Database()
    crawler = Crawler(db)
    await crawler.run()
    return len(crawler.discoveries)


def check_duplicates() -> list:
    """Check for duplicate URLs in portals.json."""
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    # Normalize URLs for comparison
    url_to_portals = {}
    for p in data['portals']:
        url = p.get('url', '')
        # Normalize: lowercase, remove www, remove trailing slash
        normalized = urlparse(url.lower())
        domain = normalized.netloc.replace('www.', '')
        key = f"{domain}{normalized.path.rstrip('/')}"

        if key not in url_to_portals:
            url_to_portals[key] = []
        url_to_portals[key].append(p)

    # Find duplicates
    duplicates = []
    for key, portals in url_to_portals.items():
        if len(portals) > 1:
            duplicates.append({
                'key': key,
                'portals': portals
            })

    return duplicates


def remove_duplicates(dry_run: bool = True) -> int:
    """Remove duplicate entries, keeping the first (usually better curated) one."""
    duplicates = check_duplicates()

    if not duplicates:
        print("✅ No duplicates found")
        return 0

    print(f"🔍 Found {len(duplicates)} duplicate URL groups:\n")

    with open(PORTALS_JSON) as f:
        data = json.load(f)

    to_remove = []
    for dup in duplicates:
        portals = dup['portals']
        # Keep first one (usually the original, better-curated entry)
        keep = portals[0]
        remove = portals[1:]

        print(f"  {dup['key']}:")
        print(f"    ✓ Keep: {keep['id']} ({keep.get('name', 'Unknown')})")
        for r in remove:
            print(f"    ✗ Remove: {r['id']} ({r.get('name', 'Unknown')})")
            to_remove.append(r['id'])
        print()

    if dry_run:
        print(f"Run with --dedup --apply to remove {len(to_remove)} duplicates")
        return len(to_remove)

    # Actually remove
    data['portals'] = [p for p in data['portals'] if p['id'] not in to_remove]

    with open(PORTALS_JSON, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Removed {len(to_remove)} duplicate entries")
    return len(to_remove)


def show_unverified(limit: int = 10):
    """Show unverified sites that need manual review in Claude Code."""
    from verify_sites import get_unverified_sites

    sites = get_unverified_sites(limit)
    if not sites:
        print("No unverified sites to check")
        return

    print(f"Found {len(sites)} unverified sites:\n")
    for site in sites:
        print(f"  • {site['domain']}: {site.get('title', '')[:50]}")

    print("\n💡 To verify these in Claude Code, say:")
    print(f'   "verify these sites: {", ".join(s["domain"] for s in sites[:5])}"')


def main():
    args = sys.argv[1:]

    # Dedup mode
    if '--dedup' in args:
        print("🔍 Checking for duplicates...\n")
        apply = '--apply' in args
        remove_duplicates(dry_run=not apply)
        return

    # Just sync mode
    if '--sync' in args:
        print("📋 Sync-only mode\n")
        sync()
        return

    # Fast mode - less brute force
    fast = '--fast' in args
    verify = '--verify' in args

    print("🦞 MOLT DISCOVERY PIPELINE")
    print("=" * 50)

    # Step 1: Run crawler
    print("\n📡 STEP 1: CRAWLING FOR NEW SITES")
    print("-" * 40)
    new_sites = asyncio.run(run_crawler(fast_mode=fast))

    # Step 2: Sync to portals.json
    print("\n📋 STEP 2: SYNCING TO PORTALS.JSON")
    print("-" * 40)
    sync()

    # Step 3: Check duplicates
    print("\n🔍 STEP 3: CHECKING FOR DUPLICATES")
    print("-" * 40)
    duplicates = check_duplicates()
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} duplicate groups. Run --dedup to review.")
    else:
        print("✅ No duplicates")

    # Step 4: Show unverified sites
    if verify:
        print("\n🔍 STEP 4: SITES NEEDING VERIFICATION")
        print("-" * 40)
        show_unverified()

    print("\n" + "=" * 50)
    print("✅ DISCOVERY COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
