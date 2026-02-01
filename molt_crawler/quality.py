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
    'llm': 2, 'claude': 2,

    # Ecosystem patterns (weight 2)
    'for agents': 2, 'for ai': 2, 'agent economy': 2,
    'agent social': 2, 'agent marketplace': 2,
}

# FALSE POSITIVES - phrases that indicate the site is NOT part of the molt ecosystem
# These should immediately disqualify a site
FALSE_POSITIVE_PHRASES = [
    # Seafood/Restaurant
    'stone crab', 'seafood restaurant', 'waterfront restaurant',
    'arctic taste', 'spice combination', 'mail-order crabs',
    'hard-shell crabs', 'we sell', 'shipped nationwide',

    # Discord/Telegram bot directories (not molt-specific)
    'discord bots', 'find bots for discord', 'discord, slack, telegram',
    'telegram, kik', 'monitoring discord servers', 'chatbot directory',
    'chatbot builder', 'open source chatbot',

    # Windows/System tools
    'windows power tools', 'shell extension', 'explorer enhancement',
    'windows add-on', 'github gists',

    # Cloud computing (non-agent)
    'your computer in the cloud',

    # Legal/Business services
    'registered agent service', 'service of process',
    'board of trade',

    # Entertainment industry (talent agents)
    'actor talent', 'talent agencies', 'actor resource',

    # Real estate
    'real estate', 'property',

    # RPA/Automation (non-molt)
    'python governance platform', 'warehouse automation',
    'rpa', 'robotic process automation',

    # Physical arcades
    'claw machine arcade', "minnesota's largest",

    # Investment/Trading (non-agent)
    'bots capital',

    # Generic religious/game site
    'let the kingdom come',

    # Recruiting/HR (non-agent)
    'automate your recruiting', 'book more interviews',

    # Generic AI tools (not molt ecosystem)
    'ai automation framework',
]

# Domains to always exclude (known false positives)
EXCLUDE_DOMAINS = [
    # Seafood
    'crabs.com', 'crabs.net', 'crab.com', 'lobsterbook.com',

    # Discord bot directories
    'botlist.net', 'botlist.xyz', 'bots.gg', 'bothunt.ai',

    # Windows tools
    'shellcity.net', 'shells.com', 'shellhub.io', 'shellbase.app',

    # Unrelated businesses
    'bot.com', 'agent.co', 'agentlist.org', 'agentworld.com',
    'botcity.dev', 'botcity.ai', 'botverse.org', 'moltnet.com',
    'clawworld.com', 'clawcity.co', 'lobster.world', 'lobsterwork.com',

    # BotWorld religious/game site (5 TLDs)
    'botworld.org', 'botworld.co', 'botworld.net', 'botworld.com', 'botworld.live',

    # Other false positives
    'bots.ai', 'bots.io', 'bot.ai', 'botbase.co', 'botnet.co',
    'bothub.bot', 'bots.co', 'shellworld.net', 'shellworld.com',

    # Generic/unrelated agent/bot sites (not molt ecosystem)
    'bot.co', 'botlist.app', 'shellnews.net', 'agentbook.org',
    'agentcity.co', 'agentcity.com', 'agentcity.io',
    'agentlist.dev', 'agentnet.xyz', 'agent.io',

    # Verified not molt ecosystem (checked actual site content)
    'agents.ai',  # Browser automation "browse-to-earn", not AI agents
    'agenthub.app',  # Real estate/insurance agents, not AI
]

# Red flags - reduce trust
RED_FLAGS = [
    'parked domain', 'domain for sale', 'coming soon',
    'under construction', 'database vulnerability', 'compromised',
    'scam', 'phishing', 'malware', 'do not use',
    'hostinger dns system', 'future home of',
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


def is_false_positive(domain: str, title: str, description: str) -> bool:
    """Check if site matches false positive patterns."""
    text = f"{title} {description}".lower()
    domain_lower = domain.lower()

    # Check excluded domains
    if domain_lower in EXCLUDE_DOMAINS:
        return True

    # Check for mailto: or invalid URLs
    if domain_lower.startswith('mailto:'):
        return True

    # Check false positive phrases
    for phrase in FALSE_POSITIVE_PHRASES:
        if phrase in text:
            return True

    return False


def calculate_relevance(domain: str, title: str, description: str) -> tuple:
    """Calculate relevance score 0-100 based on molt ecosystem keywords."""
    # First check if it's a false positive
    if is_false_positive(domain, title, description):
        return (0, ['FALSE_POSITIVE'])

    text = f"{domain} {title} {description}".lower()
    score = 0
    matches = []

    for keyword, weight in RELEVANCE_KEYWORDS.items():
        if keyword in text:
            score += weight * 10
            matches.append(keyword)

    # Bonus for domain containing core molt/claw keywords (these are ecosystem sites)
    domain_lower = domain.lower()
    is_molt_domain = any(k in domain_lower for k in ['molt', 'claw', 'lobster', 'craber'])

    if is_molt_domain:
        score += 30  # Strong bonus for molt ecosystem domains

    # Smaller bonus for 'agent' in domain (too generic alone)
    if 'agent' in domain_lower and not is_molt_domain:
        score += 10

    # Penalty for generic/minimal descriptions (but less for molt domains)
    if description == f"Discovered at {domain}" or description == domain:
        score = max(0, score - (10 if is_molt_domain else 20))

    # Penalty for descriptions that are just the domain name
    if description.lower().strip() == domain_lower.strip():
        score = max(0, score - (15 if is_molt_domain else 30))

    # Penalty for very short/generic descriptions (but less for molt domains)
    if len(description) < 20:
        score = max(0, score - (5 if is_molt_domain else 10))

    # Cap at 100
    return (min(100, score), matches)


def calculate_trust(domain: str, title: str, description: str, notes: str = "") -> str:
    """Determine trust level based on content and flags."""
    text = f"{domain} {title} {description} {notes}".lower()

    # Check if it's a false positive - always untrusted
    if is_false_positive(domain, title, description):
        return 'untrusted'

    # Check for red flags
    for flag in RED_FLAGS:
        if flag in text:
            return 'untrusted'

    # Check relevance
    relevance, matches = calculate_relevance(domain, title, description)

    # If marked as false positive
    if 'FALSE_POSITIVE' in matches:
        return 'untrusted'

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
    false_positives = []

    for portal in data['portals']:
        domain = portal.get('url', '').replace('https://', '').replace('http://', '').split('/')[0]
        title = portal.get('name', '')
        description = portal.get('description', '')
        notes = portal.get('notes', '')

        # Calculate scores
        relevance, keywords = calculate_relevance(domain, title, description)

        # Check if already has manual trust override
        if portal.get('verified'):
            trust = 'verified'
        elif 'FALSE_POSITIVE' in keywords:
            trust = 'untrusted'
            false_positives.append(domain)
        else:
            trust = calculate_trust(domain, title, description, notes)

        # Update portal
        portal['relevance'] = relevance
        portal['trust'] = trust

        stats[trust] = stats.get(trust, 0) + 1

        # Show low quality for review
        if trust in ['low', 'untrusted']:
            reason = 'FALSE_POSITIVE' if 'FALSE_POSITIVE' in keywords else ''
            print(f"  ⚠️  {domain}: trust={trust}, relevance={relevance} {reason}")

    # Save
    with open(PORTALS_JSON, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Quality Distribution:")
    print(f"  ✅ Verified: {stats.get('verified', 0)}")
    print(f"  🟢 High trust: {stats.get('high', 0)}")
    print(f"  🟡 Medium trust: {stats.get('medium', 0)}")
    print(f"  🟠 Low trust: {stats.get('low', 0)}")
    print(f"  🔴 Untrusted: {stats.get('untrusted', 0)}")

    if false_positives:
        print(f"\n🚫 Detected {len(false_positives)} false positives:")
        for fp in false_positives[:10]:
            print(f"    - {fp}")
        if len(false_positives) > 10:
            print(f"    ... and {len(false_positives) - 10} more")


def cleanup_false_positives():
    """Remove known false positive sites from portals.json."""
    with open(PORTALS_JSON) as f:
        data = json.load(f)

    removed = []

    # Filter out false positives
    cleaned_portals = []
    for portal in data['portals']:
        domain = portal.get('url', '').replace('https://', '').replace('http://', '').split('/')[0]
        title = portal.get('name', '')
        description = portal.get('description', '')

        if is_false_positive(domain, title, description):
            removed.append(domain)
        else:
            cleaned_portals.append(portal)

    data['portals'] = cleaned_portals

    # Save
    with open(PORTALS_JSON, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"🧹 Cleanup complete:")
    print(f"   Removed: {len(removed)} false positives")
    print(f"   Remaining: {len(cleaned_portals)} portals")

    if removed:
        print(f"\n🚫 Removed sites:")
        for domain in removed:
            print(f"    - {domain}")


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
        elif sys.argv[1] == '--cleanup':
            cleanup_false_positives()
        else:
            print("Usage: quality.py [--featured|--audit|--export|--cleanup]")
    else:
        score_portals()
