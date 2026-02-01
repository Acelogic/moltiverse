#!/usr/bin/env python3
"""
Site verification helper for molt ecosystem.
Outputs unverified sites for Claude Code to verify using WebFetch.

Usage:
    python3 verify_sites.py              # List unverified sites
    python3 verify_sites.py --json       # Output as JSON for processing
    python3 verify_sites.py --limit N    # Limit to N sites

Then in Claude Code, ask: "verify these sites" and it will use WebFetch + subagents.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# File paths
CRAWLER_DB = Path(__file__).parent / "molt_sites_db.json"
PORTALS_JSON = Path(__file__).parent.parent / "portals.json"
EXCLUDED_JSON = Path(__file__).parent / "excluded_sites.json"


def load_excluded() -> set:
    """Load excluded domains."""
    if EXCLUDED_JSON.exists():
        with open(EXCLUDED_JSON) as f:
            data = json.load(f)
            return set(data.get('excluded', {}).keys())
    return set()


def load_portals() -> set:
    """Load existing portal domains."""
    if PORTALS_JSON.exists():
        with open(PORTALS_JSON) as f:
            data = json.load(f)
            domains = set()
            for p in data.get('portals', []):
                url = p.get('url', '')
                domain = urlparse(url).netloc.replace('www.', '')
                domains.add(domain)
            return domains
    return set()


def get_unverified_sites(limit: int = 20) -> list:
    """Get sites from crawler DB that aren't in portals or exclusions."""
    if not CRAWLER_DB.exists():
        return []

    with open(CRAWLER_DB) as f:
        db = json.load(f)

    sites = db.get('sites', {})
    existing_portals = load_portals()
    excluded = load_excluded()

    unverified = []
    for url, info in sites.items():
        if not info.get('alive') or not info.get('has_real_content'):
            continue

        domain = urlparse(url if url.startswith('http') else f'https://{url}').netloc.replace('www.', '')

        # Skip if already processed
        if domain in existing_portals or domain in excluded:
            continue

        unverified.append({
            'url': info.get('url', f'https://{domain}'),
            'domain': domain,
            'title': info.get('title', '')
        })

        if len(unverified) >= limit:
            break

    return unverified


def check_duplicates() -> list:
    """Check for duplicate URLs in portals.json."""
    if not PORTALS_JSON.exists():
        return []

    with open(PORTALS_JSON) as f:
        data = json.load(f)

    url_to_portals = {}
    for p in data['portals']:
        url = p.get('url', '')
        normalized = urlparse(url.lower())
        domain = normalized.netloc.replace('www.', '')
        key = f"{domain}{normalized.path.rstrip('/')}"

        if key not in url_to_portals:
            url_to_portals[key] = []
        url_to_portals[key].append(p)

    duplicates = []
    for key, portals in url_to_portals.items():
        if len(portals) > 1:
            duplicates.append({
                'key': key,
                'count': len(portals),
                'ids': [p['id'] for p in portals]
            })

    return duplicates


def main():
    args = sys.argv[1:]

    as_json = '--json' in args
    limit = 20

    for i, arg in enumerate(args):
        if arg == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])

    # Check for duplicates first
    duplicates = check_duplicates()
    if duplicates and not as_json:
        print(f"⚠️  Found {len(duplicates)} duplicate URL groups in portals.json")
        print("   Run: python3 discover.py --dedup\n")

    # Get unverified sites
    sites = get_unverified_sites(limit)

    if as_json:
        print(json.dumps({
            'unverified': sites,
            'duplicates': duplicates
        }, indent=2))
        return

    if not sites:
        print("✅ No unverified sites found")
        print("\nAll discovered sites are either in portals.json or excluded_sites.json")
        return

    print(f"🔍 Found {len(sites)} unverified sites:\n")

    for i, site in enumerate(sites, 1):
        print(f"{i}. {site['domain']}")
        if site['title']:
            print(f"   Title: {site['title'][:60]}")
        print(f"   URL: {site['url']}")
        print()

    print("-" * 50)
    print("To verify these in Claude Code, say:")
    print('  "verify these sites: ' + ', '.join(s['domain'] for s in sites[:5]) + '"')
    print("\nOr copy the URLs and ask Claude Code to check if they're agent-usable.")


if __name__ == "__main__":
    main()
