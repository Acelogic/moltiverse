#!/usr/bin/env python3
"""
Sync crawler discoveries to portals.json
Merges new sites from molt_sites_db.json into the website's portals.json
"""

import json
from pathlib import Path
from datetime import datetime

# Paths
CRAWLER_DB = Path(__file__).parent / "molt_sites_db.json"
PORTALS_JSON = Path(__file__).parent.parent / "portals.json"

# Category detection based on keywords in domain/title
CATEGORY_RULES = [
    # (keywords, category, tag, icon)
    (['news', 'feed', 'wire'], 'platform', 'News', '📰'),
    (['social', 'book', 'chat', 'talk', 'forum', 'chan'], 'social', 'Social', '💬'),
    (['photo', 'image', 'pic', 'insta', 'gram'], 'creative', 'Photo Sharing', '📸'),
    (['video', 'hub', 'tube', 'stream'], 'creative', 'Video', '🎬'),
    (['game', 'play', 'arcade', 'mmo'], 'gaming', 'Gaming', '🎮'),
    (['market', 'shop', 'store', 'trade', 'list', 'classified'], 'platform', 'Marketplace', '🏪'),
    (['job', 'work', 'hire', 'gig', 'freelance'], 'platform', 'Jobs', '💼'),
    (['hunt', 'discover', 'find', 'search', 'directory'], 'platform', 'Discovery', '🔍'),
    (['church', 'temple', 'community', 'group'], 'social', 'Community', '⛪'),
    (['bot', 'agent', 'ai', 'auto'], 'platform', 'AI Platform', '🤖'),
    (['dev', 'code', 'api', 'tool'], 'platform', 'Developer', '🔧'),
    (['art', 'creative', 'draw', 'canvas', 'pixel'], 'creative', 'Creative', '🎨'),
    (['match', 'date', 'connect', 'meet'], 'social', 'Matching', '💕'),
    (['bounty', 'reward', 'task'], 'platform', 'Bounties', '🎯'),
    (['ship', 'build', 'launch'], 'platform', 'Shipping', '🚀'),
]

# Default icon by category
DEFAULT_ICONS = {
    'social': '💬',
    'creative': '🎨',
    'gaming': '🎮',
    'platform': '🔧',
}

# Molt-specific icons
MOLT_ICONS = {
    'molt': '🦞',
    'claw': '🦀',
    'lobster': '🦞',
    'crab': '🦀',
    'shell': '🐚',
}


def detect_category(domain: str, title: str) -> tuple:
    """Detect category, tag, and icon from domain/title."""
    text = f"{domain} {title}".lower()

    # Check molt-specific icons first
    for keyword, icon in MOLT_ICONS.items():
        if keyword in domain.lower():
            # Continue to find category
            for keywords, category, tag, _ in CATEGORY_RULES:
                if any(k in text for k in keywords):
                    return category, tag, icon
            return 'platform', 'Agent Platform', icon

    # Check category rules
    for keywords, category, tag, icon in CATEGORY_RULES:
        if any(k in text for k in keywords):
            return category, tag, icon

    # Default
    return 'platform', 'Platform', '🌐'


def domain_to_name(domain: str, title: str) -> str:
    """Convert domain to display name."""
    # If title exists and is meaningful, use it
    if title and len(title) > 3 and not title.startswith('http'):
        # Clean up title
        name = title.split('|')[0].split('-')[0].split('—')[0].strip()
        if len(name) > 3 and len(name) < 50:
            return name

    # Otherwise, format domain
    name = domain.replace('.com', '').replace('.io', '').replace('.ai', '')
    name = name.replace('.app', '').replace('.org', '').replace('.xyz', '')
    name = name.replace('-', ' ').replace('_', ' ')
    return name.title()


def domain_to_id(domain: str) -> str:
    """Convert domain to ID."""
    return domain.replace('.', '-').replace('_', '-').lower()


def load_crawler_db() -> dict:
    """Load the crawler database."""
    if not CRAWLER_DB.exists():
        print(f"Crawler DB not found: {CRAWLER_DB}")
        return {}

    with open(CRAWLER_DB) as f:
        return json.load(f)


def load_portals() -> dict:
    """Load existing portals.json."""
    if not PORTALS_JSON.exists():
        return {"updated": "", "portals": [], "categories": []}

    with open(PORTALS_JSON) as f:
        return json.load(f)


def sync():
    """Sync crawler discoveries to portals.json."""
    print("🔄 Syncing crawler discoveries to portals.json...")

    # Load data
    crawler_data = load_crawler_db()
    portals_data = load_portals()

    if not crawler_data.get('sites'):
        print("No sites in crawler DB")
        return

    # Get existing portal URLs
    existing_urls = {p['url'].rstrip('/').lower() for p in portals_data.get('portals', [])}
    existing_domains = {p['url'].split('//')[1].split('/')[0].lower() for p in portals_data.get('portals', [])}

    # Filter and convert new sites
    new_portals = []
    for domain, info in crawler_data['sites'].items():
        # Skip if not alive or no content
        if not info.get('alive') or not info.get('has_content'):
            continue

        # Skip if already exists
        url = info.get('url', f"https://{domain}").rstrip('/')
        domain_clean = domain.lower().replace('www.', '')

        if url.lower() in existing_urls or domain_clean in existing_domains:
            continue

        # Skip subdomains of known sites (e.g., user.moltcities.org)
        if any(domain_clean.endswith(f".{d}") for d in existing_domains):
            continue

        # Detect category
        title = info.get('title', '')
        category, tag, icon = detect_category(domain, title)

        # Create portal entry
        portal = {
            "id": domain_to_id(domain),
            "name": domain_to_name(domain, title),
            "url": url,
            "icon": icon,
            "category": category,
            "tag": tag,
            "description": title[:150] if title else f"Discovered at {domain}",
            "discovered": info.get('first_seen', datetime.now().isoformat())[:10]
        }

        new_portals.append(portal)
        print(f"  + {domain}: {portal['name']} ({category})")

    if not new_portals:
        print("No new portals to add")
        return

    # Merge - add new portals at the end
    portals_data['portals'].extend(new_portals)
    portals_data['updated'] = datetime.now().strftime('%Y-%m-%d')

    # Ensure categories exist
    if 'categories' not in portals_data:
        portals_data['categories'] = [
            {"id": "all", "name": "All", "icon": "🌐"},
            {"id": "social", "name": "Social", "icon": "💬"},
            {"id": "creative", "name": "Creative", "icon": "🎨"},
            {"id": "platform", "name": "Platform", "icon": "🔧"},
            {"id": "gaming", "name": "Gaming", "icon": "🎮"}
        ]

    # Save
    with open(PORTALS_JSON, 'w') as f:
        json.dump(portals_data, f, indent=2)

    print(f"\n✅ Added {len(new_portals)} new portals")
    print(f"📁 Total portals: {len(portals_data['portals'])}")
    print(f"💾 Saved to {PORTALS_JSON}")


def run_quality_check():
    """Run quality scoring after sync."""
    try:
        from quality import score_portals
        print("\n📊 Running quality check...")
        score_portals()
    except ImportError:
        print("Quality module not found, skipping quality check")


if __name__ == "__main__":
    sync()
    run_quality_check()
