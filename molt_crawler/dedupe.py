#!/usr/bin/env python3
"""
Deduplicate portals with same base name but different TLDs.
Keeps the highest-quality version of each.
"""

import json
from pathlib import Path
from collections import defaultdict

PORTALS_JSON = Path(__file__).parent.parent / "portals.json"

# TLD preference order (higher = better)
TLD_PRIORITY = {
    '.com': 100,
    '.io': 90,
    '.ai': 85,
    '.app': 80,
    '.dev': 75,
    '.org': 70,
    '.net': 65,
    '.co': 60,
    '.xyz': 50,
    '.live': 45,
    '.bot': 40,
    '.space': 35,
    '.town': 30,
    '.gg': 25,
}

# Known different sites with same base name (don't dedupe these)
KNOWN_DIFFERENT = {
    # moltbook.com (social network) vs moltbook.town (pixel visualization)
    ('moltbook.com', 'moltbook.town'),
    # Different products
    ('clawcity.app', 'clawcity.xyz'),
    # molt.church is a real different site (Church of Molt)
    ('molt.bot', 'molt.church'),
    ('moltbook.com', 'molt.church'),
}


def get_base_name(url: str) -> str:
    """Extract base name from URL (without TLD)."""
    domain = url.split('//')[1].split('/')[0].replace('www.', '').lower()
    # Handle multi-part TLDs
    for tld in sorted(TLD_PRIORITY.keys(), key=len, reverse=True):
        if domain.endswith(tld):
            return domain[:-len(tld)]
    # Fallback: split on last dot
    parts = domain.rsplit('.', 1)
    return parts[0] if len(parts) > 1 else domain


def get_tld(url: str) -> str:
    """Extract TLD from URL."""
    domain = url.split('//')[1].split('/')[0].replace('www.', '').lower()
    for tld in sorted(TLD_PRIORITY.keys(), key=len, reverse=True):
        if domain.endswith(tld):
            return tld
    parts = domain.rsplit('.', 1)
    return '.' + parts[1] if len(parts) > 1 else ''


def score_portal(portal: dict) -> int:
    """Score a portal for quality (higher = better)."""
    score = 0

    # TLD priority
    tld = get_tld(portal['url'])
    score += TLD_PRIORITY.get(tld, 20)

    # Relevance score
    score += portal.get('relevance', 0)

    # Trust level bonus
    trust_bonus = {
        'verified': 100,
        'high': 50,
        'medium': 25,
        'low': 0,
        'untrusted': -50,
    }
    score += trust_bonus.get(portal.get('trust', 'low'), 0)

    # Has real description (not just domain name)
    desc = portal.get('description', '')
    if desc and 'Parked' not in desc and 'Hostinger' not in desc:
        score += 20

    # Featured bonus
    if portal.get('featured'):
        score += 30

    return score


def is_known_different(url1: str, url2: str) -> bool:
    """Check if two URLs are known to be different sites."""
    domain1 = url1.split('//')[1].split('/')[0].replace('www.', '').lower()
    domain2 = url2.split('//')[1].split('/')[0].replace('www.', '').lower()

    return (domain1, domain2) in KNOWN_DIFFERENT or (domain2, domain1) in KNOWN_DIFFERENT


def find_duplicates():
    """Find and report duplicate portals."""
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    # Group by base name
    by_base = defaultdict(list)
    for portal in data['portals']:
        base = get_base_name(portal['url'])
        by_base[base].append(portal)

    # Find groups with multiple entries
    duplicates = {k: v for k, v in by_base.items() if len(v) > 1}

    print(f"🔍 Found {len(duplicates)} base names with multiple TLDs\n")

    to_remove = []

    for base, portals in sorted(duplicates.items()):
        # Skip if all are known to be different
        urls = [p['url'] for p in portals]
        all_different = all(
            is_known_different(urls[i], urls[j])
            for i in range(len(urls))
            for j in range(i+1, len(urls))
        )
        if all_different:
            continue

        # Score each portal
        scored = [(score_portal(p), p) for p in portals]
        scored.sort(key=lambda x: x[0], reverse=True)

        # Keep the best one
        best_score, best = scored[0]
        rest = scored[1:]

        # Only flag as duplicate if scores are similar or rest are low quality
        for score, portal in rest:
            # Skip if known different
            if is_known_different(best['url'], portal['url']):
                continue

            # If the other one is much worse, it's likely a dupe or parked
            if score < best_score - 30 or portal.get('trust') in ['low', 'untrusted']:
                to_remove.append(portal)
                print(f"  ❌ {portal['url']:40} (score: {score})")

        if rest and not all(is_known_different(best['url'], p['url']) for _, p in rest):
            print(f"  ✅ {best['url']:40} (score: {best_score}) <- KEEP")
            print()

    return to_remove


def dedupe(dry_run=True):
    """Remove duplicate portals."""
    to_remove = find_duplicates()

    if not to_remove:
        print("No duplicates to remove")
        return

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Would remove {len(to_remove)} duplicates")

    if dry_run:
        print("\nRun with --apply to actually remove them")
        return

    with open(PORTALS_JSON) as f:
        data = json.load(f)

    remove_urls = {p['url'] for p in to_remove}
    data['portals'] = [p for p in data['portals'] if p['url'] not in remove_urls]

    with open(PORTALS_JSON, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Removed {len(to_remove)} duplicates")
    print(f"📁 Remaining: {len(data['portals'])} portals")


if __name__ == "__main__":
    import sys
    dry_run = '--apply' not in sys.argv
    dedupe(dry_run)
