#!/usr/bin/env python3
"""
Quality scoring for molt ecosystem sites.
Adds relevance scores, trust levels, and status tracking.
"""

import json
import re
from pathlib import Path
from datetime import datetime

PORTALS_JSON = Path(__file__).parent.parent / "portals.json"

# Relevance keywords - higher weight = more relevant
RELEVANCE_KEYWORDS = {
    # Core molt ecosystem (weight 3)
    'molt': 3, 'claw': 3, 'openclaw': 3, 'lobster': 3,
    'moltbook': 3, 'crustacean': 3, 'moltverse': 3,

    # Agent-specific (weight 2)
    'agent': 2, 'ai agent': 2, 'autonomous': 2, 'agentic': 2,
    'bot': 1, 'llm': 2, 'claude': 2, 'gpt': 1,

    # Ecosystem patterns (weight 2)
    'for agents': 2, 'for ai': 2, 'agent economy': 2,
    'agent social': 2, 'agent marketplace': 2,
}

# Red flags - reduce trust
RED_FLAGS = [
    'parked domain', 'domain for sale', 'coming soon',
    'under construction', 'database vulnerability', 'compromised',
    'scam', 'phishing', 'malware', 'do not use',
]

# Quality categories
TRUST_LEVELS = {
    'verified': 'Manually verified, trusted',
    'high': 'Real content, clearly molt ecosystem',
    'medium': 'Real content, possibly related',
    'low': 'Minimal content or unclear relevance',
    'untrusted': 'Known issues or security concerns',
}

# Status values
STATUS_VALUES = ['active', 'inactive', 'down', 'compromised', 'parked']


def calculate_relevance(domain: str, title: str, description: str) -> tuple:
    """Calculate relevance score 0-100 based on molt ecosystem keywords."""
    text = f"{domain} {title} {description}".lower()
    score = 0
    matches = []

    for keyword, weight in RELEVANCE_KEYWORDS.items():
        if keyword in text:
            score += weight * 10
            matches.append(keyword)

    # Bonus for domain containing core keywords
    if any(k in domain.lower() for k in ['molt', 'claw', 'lobster', 'agent']):
        score += 20

    # Cap at 100
    return (min(100, score), matches)


def calculate_trust(domain: str, title: str, description: str, notes: str = "") -> str:
    """Determine trust level based on content and flags."""
    text = f"{domain} {title} {description} {notes}".lower()

    # Check for red flags
    for flag in RED_FLAGS:
        if flag in text:
            return 'untrusted'

    # Check relevance
    relevance, _ = calculate_relevance(domain, title, description)

    if relevance >= 60:
        return 'high'
    elif relevance >= 30:
        return 'medium'
    else:
        return 'low'


def score_portals():
    """Add quality scores to all portals."""
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    print("🔍 Scoring portals for quality...\n")

    stats = {'high': 0, 'medium': 0, 'low': 0, 'untrusted': 0, 'verified': 0}

    for portal in data['portals']:
        domain = portal.get('url', '').replace('https://', '').replace('http://', '').split('/')[0]
        title = portal.get('name', '')
        description = portal.get('description', '')
        notes = portal.get('notes', '')

        # Calculate scores
        relevance, keywords = calculate_relevance(domain, title, description)
        trust = portal.get('trust', calculate_trust(domain, title, description, notes))

        # Keep verified status if already set
        if portal.get('verified'):
            trust = 'verified'

        # Update portal
        portal['relevance'] = relevance
        portal['trust'] = trust

        stats[trust] = stats.get(trust, 0) + 1

        # Show low quality for review
        if trust in ['low', 'untrusted']:
            print(f"  ⚠️  {domain}: trust={trust}, relevance={relevance}")

    # Save
    with open(PORTALS_JSON, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Quality Distribution:")
    print(f"  ✅ Verified: {stats.get('verified', 0)}")
    print(f"  🟢 High trust: {stats.get('high', 0)}")
    print(f"  🟡 Medium trust: {stats.get('medium', 0)}")
    print(f"  🟠 Low trust: {stats.get('low', 0)}")
    print(f"  🔴 Untrusted: {stats.get('untrusted', 0)}")


def filter_quality(min_trust: str = 'medium', min_relevance: int = 30):
    """Get only quality portals meeting minimum thresholds."""
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    trust_order = ['untrusted', 'low', 'medium', 'high', 'verified']
    min_trust_idx = trust_order.index(min_trust)

    quality_portals = []
    for portal in data['portals']:
        trust = portal.get('trust', 'low')
        relevance = portal.get('relevance', 0)
        trust_idx = trust_order.index(trust) if trust in trust_order else 0

        if trust_idx >= min_trust_idx and relevance >= min_relevance:
            quality_portals.append(portal)

    return quality_portals


def mark_featured():
    """Automatically mark high-quality portals as featured."""
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    # Featured = verified OR (high trust AND relevance >= 60)
    featured_count = 0
    for portal in data['portals']:
        if portal.get('verified') or (portal.get('trust') == 'high' and portal.get('relevance', 0) >= 60):
            if not portal.get('featured'):
                portal['featured'] = True
                featured_count += 1
                print(f"  ⭐ Featured: {portal.get('name')}")

    with open(PORTALS_JSON, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Marked {featured_count} new portals as featured")


def audit_low_quality():
    """Show all low/untrusted sites for manual review."""
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    low_quality = [p for p in data['portals'] if p.get('trust') in ['low', 'untrusted']]

    print(f"🔍 AUDIT: {len(low_quality)} sites need review\n")
    print("-" * 60)

    for p in sorted(low_quality, key=lambda x: x.get('relevance', 0)):
        domain = p['url'].replace('https://', '').replace('http://', '').split('/')[0]
        trust = p.get('trust', 'unknown')
        relevance = p.get('relevance', 0)
        print(f"{trust:10} | rel:{relevance:3} | {domain}")
        print(f"           | {p.get('description', '')[:50]}")
        print()

    print("-" * 60)
    print("To upgrade a site, edit portals.json and set:")
    print('  "trust": "medium"  or  "verified": true')


def export_audit_csv():
    """Export low-quality sites to CSV for spreadsheet review."""
    import csv
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    csv_path = Path(__file__).parent / "audit_queue.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['domain', 'name', 'trust', 'relevance', 'description', 'action'])

        for p in data['portals']:
            if p.get('trust') in ['low', 'untrusted']:
                domain = p['url'].replace('https://', '').replace('http://', '').split('/')[0]
                writer.writerow([
                    domain,
                    p.get('name', ''),
                    p.get('trust', ''),
                    p.get('relevance', 0),
                    p.get('description', '')[:100],
                    ''  # action column for manual input
                ])

    print(f"📄 Exported to {csv_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == '--featured':
            score_portals()
            mark_featured()
        elif sys.argv[1] == '--audit':
            audit_low_quality()
        elif sys.argv[1] == '--export':
            export_audit_csv()
        else:
            print("Usage: quality.py [--featured|--audit|--export]")
    else:
        score_portals()
