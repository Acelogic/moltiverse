#!/usr/bin/env python3
"""
Quality scoring for molt ecosystem sites.
Adds relevance scores, trust levels, and status tracking.
Now uses JSON files for exclusions instead of hardcoded lists.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta

# File paths
PORTALS_JSON = Path(__file__).parent.parent / "portals.json"
EXCLUDED_JSON = Path(__file__).parent / "excluded_sites.json"
AUDIT_LOG_JSON = Path(__file__).parent / "audit_log.json"

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

# Auto-detection patterns for bad sites
# Key principle: We want sites USABLE BY agents, not sites ABOUT agents or FOR humans
AUTO_DETECT_BAD = {
    'parked_page': [
        'launching soon', 'coming soon', 'bald geht\'s los',
        'we\'re getting things ready', 'under construction',
        'future home of', 'parked domain', 'domain for sale',
        'hostinger dns system', 'godaddy', 'this domain is for sale',
        'wix thunderbolt', 'wix-hosted',  # Empty Wix sites
    ],
    'for_humans': [
        # Agent development tools (for humans to BUILD agents)
        # Be specific - these phrases indicate the site IS FOR building, not just mentioning it
        'platform built for developers',
        'no-code automation platform', 'workflow automation platform',
        'automate your workflows', 'business automation platform',
        # Chatbot builders (humans building chatbots, not agent-usable)
        'chatbot builder', 'build chatbots', 'create chatbots',
        'conversational ai platform built for',
        # AI directories (listing agents for humans to browse)
        'ai agent directory', 'find the right ai agent',
        'discover ai agents', 'browse ai agents',
        'curated directory of ai agents',
    ],
    'wrong_industry': [
        # Seafood
        'stone crab', 'seafood restaurant', 'waterfront restaurant',
        'mail-order crabs', 'hard-shell crabs', 'shipped nationwide',
        # Real estate
        'real estate', 'property listing', 'agents who sell',
        'realtors', 'home buying',
        # Insurance/Medicare
        'medicare', 'insurance agent', 'life insurance',
        # Talent/HR
        'talent agencies', 'actor resource', 'recruiting',
        # Physical products
        'electric fencing', 'poultry supplies', 'excavator',
        # Fashion
        'clothing brand', 'fashion retail',
        # Travel agents (human, not AI)
        'travel agent training', 'travel incentives', 'travel professionals',
        # Legal registered agents
        'registered agent service', 'registered agent for',
        'corporations, llcs', 'annual report tracking',
        # Physical arcades
        'claw machine arcade', 'arcade entertainment', 'claw arcade',
        'party packages', 'arcade games',
        # Cleaning/maintenance
        'limpieza', 'cleaning services', 'maintenance company',
        'window cleaning', 'pool maintenance',
        # Electronics manufacturing
        'display technology', 'display panels', 'au optronics',
        'micro led', 'automotive display',
    ],
    'generic_platform': [
        'discord bots', 'telegram bot builder', 'whatsapp business',
        'chatbot directory', 'open source chatbot',
        'prediction market', 'polymarket',
        'genealogy', 'family history', 'surname research',
        # Tech news (not agent platforms)
        'tech news aggregation', 'curated content from',
        'development news', 'jstack',
        # Link management
        'link management platform', 'branded short links',
        'url shortener', 'link shortening',
    ],
    'malicious': [
        'scam', 'phishing', 'malware', 'compromised',
        '博天堂', '体育官网',  # Chinese gambling spam
    ],
}

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


def load_excluded_domains() -> dict:
    """Load excluded domains from JSON file."""
    if EXCLUDED_JSON.exists():
        with open(EXCLUDED_JSON) as f:
            data = json.load(f)
            return data.get('excluded', {})
    return {}


def save_excluded_domains(excluded: dict):
    """Save excluded domains to JSON file."""
    data = {
        'excluded': excluded,
        'updated': datetime.now().strftime('%Y-%m-%d')
    }
    with open(EXCLUDED_JSON, 'w') as f:
        json.dump(data, f, indent=2)


def log_audit(action: str, site: str = None, reason: str = None, count: int = None):
    """Log an audit action."""
    if AUDIT_LOG_JSON.exists():
        with open(AUDIT_LOG_JSON) as f:
            data = json.load(f)
    else:
        data = {'log': []}

    entry = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'action': action,
    }
    if site:
        entry['site'] = site
    if reason:
        entry['reason'] = reason
    if count is not None:
        entry['count'] = count

    data['log'].append(entry)

    with open(AUDIT_LOG_JSON, 'w') as f:
        json.dump(data, f, indent=2)


def exclude_site(domain: str, reason: str, category: str = 'other'):
    """Add a site to the exclusion list."""
    excluded = load_excluded_domains()

    excluded[domain] = {
        'reason': reason,
        'category': category,
        'checked': datetime.now().strftime('%Y-%m-%d'),
        'recheck_after': (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
    }

    save_excluded_domains(excluded)
    log_audit('exclude', site=domain, reason=reason)
    print(f"  ❌ Excluded: {domain} ({reason})")


def auto_detect_bad_site(domain: str, title: str, description: str) -> tuple:
    """
    Automatically detect if a site is bad based on content patterns.
    Returns (is_bad, category, reason) tuple.
    """
    text = f"{title} {description}".lower()

    for category, patterns in AUTO_DETECT_BAD.items():
        for pattern in patterns:
            if pattern in text:
                return (True, category, f"Auto-detected: '{pattern}'")

    # Check for minimal content (description is just domain or very short)
    if description.lower().strip() == domain.lower().strip():
        return (True, 'minimal_content', 'Description same as domain')

    if len(description) < 15 and 'molt' not in domain.lower() and 'claw' not in domain.lower():
        return (True, 'minimal_content', 'Very short description, not molt domain')

    return (False, None, None)


def is_false_positive(domain: str, title: str, description: str) -> bool:
    """Check if site matches false positive patterns."""
    text = f"{title} {description}".lower()
    domain_lower = domain.lower().replace('www.', '')

    # Check excluded domains from JSON
    excluded = load_excluded_domains()
    if domain_lower in excluded:
        return True

    # Check for mailto: or invalid URLs
    if domain_lower.startswith('mailto:'):
        return True

    # Auto-detect bad sites
    is_bad, category, reason = auto_detect_bad_site(domain_lower, title, description)
    if is_bad:
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
        domain = portal.get('url', '').replace('https://', '').replace('http://', '').split('/')[0].replace('www.', '')
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
        log_audit('cleanup', count=len(removed), reason=f"Removed: {', '.join(removed[:5])}...")
        print(f"\n🚫 Removed sites:")
        for domain in removed:
            print(f"    - {domain}")


def show_excluded():
    """Show all excluded domains with reasons."""
    excluded = load_excluded_domains()

    print(f"📋 Excluded Sites ({len(excluded)} total)\n")

    # Group by category
    by_category = {}
    for domain, info in excluded.items():
        cat = info.get('category', 'other')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((domain, info))

    for category, sites in sorted(by_category.items()):
        print(f"\n{category.upper()} ({len(sites)}):")
        for domain, info in sorted(sites):
            print(f"  {domain:35} | {info.get('reason', 'Unknown')[:40]}")


def needs_recheck():
    """Show sites that need re-verification."""
    excluded = load_excluded_domains()
    today = datetime.now().strftime('%Y-%m-%d')

    needs_check = []
    for domain, info in excluded.items():
        recheck = info.get('recheck_after', '2099-12-31')
        if recheck <= today:
            needs_check.append((domain, info))

    if needs_check:
        print(f"🔄 {len(needs_check)} sites need re-verification:\n")
        for domain, info in needs_check:
            print(f"  {domain} (last checked: {info.get('checked', 'Unknown')})")
    else:
        print("✅ No sites need re-verification")


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


def show_stats():
    """Show overall statistics."""
    excluded = load_excluded_domains()

    with open(PORTALS_JSON) as f:
        data = json.load(f)

    portals = data['portals']

    print("📊 MOLT ECOSYSTEM STATS\n")
    print(f"Total portals: {len(portals)}")
    print(f"Excluded sites: {len(excluded)}")

    # Trust distribution
    by_trust = {}
    for p in portals:
        t = p.get('trust', 'unknown')
        by_trust[t] = by_trust.get(t, 0) + 1

    print(f"\nTrust Distribution:")
    for t in ['verified', 'high', 'medium', 'low', 'untrusted']:
        print(f"  {t:12}: {by_trust.get(t, 0)}")

    # Exclusion categories
    by_cat = {}
    for domain, info in excluded.items():
        cat = info.get('category', 'other')
        by_cat[cat] = by_cat.get(cat, 0) + 1

    print(f"\nExclusion Categories:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cat:20}: {count}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == '--featured':
            score_portals()
            mark_featured()
        elif cmd == '--audit':
            audit_low_quality()
        elif cmd == '--cleanup':
            cleanup_false_positives()
        elif cmd == '--excluded':
            show_excluded()
        elif cmd == '--recheck':
            needs_recheck()
        elif cmd == '--stats':
            show_stats()
        elif cmd == '--exclude' and len(sys.argv) >= 4:
            domain = sys.argv[2]
            reason = ' '.join(sys.argv[3:])
            exclude_site(domain, reason)
        else:
            print("Usage: quality.py [command]")
            print("Commands:")
            print("  (none)      - Score all portals")
            print("  --cleanup   - Remove false positives")
            print("  --featured  - Mark high-quality as featured")
            print("  --audit     - Show low-quality sites for review")
            print("  --excluded  - Show all excluded domains")
            print("  --recheck   - Show sites needing re-verification")
            print("  --stats     - Show overall statistics")
            print("  --exclude DOMAIN REASON - Add site to exclusion list")
    else:
        score_portals()
