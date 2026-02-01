#!/usr/bin/env python3
"""
LLM-powered site verification for molt ecosystem.
Verifies if discovered sites are actually agent-usable platforms.

Usage:
    python3 verify_sites.py                    # Verify new unverified sites
    python3 verify_sites.py --url URL          # Verify a single URL
    python3 verify_sites.py --batch FILE       # Verify sites from file (one URL per line)
    python3 verify_sites.py --recheck          # Re-verify sites marked for recheck

Requires: ANTHROPIC_API_KEY environment variable
"""

import os
import sys
import json
import asyncio
import aiohttp
import ssl
import certifi
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import argparse

# Check for API key early
if not os.environ.get('ANTHROPIC_API_KEY'):
    print("Error: ANTHROPIC_API_KEY environment variable required")
    print("Set it with: export ANTHROPIC_API_KEY='your-key'")
    sys.exit(1)

import anthropic

# File paths
CRAWLER_DB = Path(__file__).parent / "molt_sites_db.json"
PORTALS_JSON = Path(__file__).parent.parent / "portals.json"
EXCLUDED_JSON = Path(__file__).parent / "excluded_sites.json"
VERIFICATION_CACHE = Path(__file__).parent / "verification_cache.json"

# Verification prompt
VERIFICATION_PROMPT = """Analyze this website and determine if it's a platform that AI agents can USE as users.

**INCLUDE** - Platforms where AI agents are the PRIMARY USERS:
- Social networks for agents (like Moltbook, MoltX)
- Forums/imageboards for agents (like 4claw, Lobchan)
- Marketplaces where agents transact (like Clawdslist)
- Games playable by agents (like ClawCity)
- Creative platforms for agents (like Molt-Place pixel canvas)
- Professional networks for agents (like PinchedIn)

**EXCLUDE** - Sites that are ABOUT agents or FOR humans:
- Agent development tools/SDKs (for humans to BUILD agents)
- AI directories listing agents (for humans to BROWSE)
- News sites about AI/agents (for humans to READ)
- No-code automation platforms
- Chatbot builders
- API platforms for developers
- Infrastructure/protocol sites

**ALSO EXCLUDE**:
- Parked/coming soon pages
- Redirects to unrelated sites
- Seafood restaurants, real estate, insurance, etc.
- Generic bot directories (Discord bots, Telegram bots)

Website URL: {url}
Website Title: {title}
Website Content:
{content}

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "verdict": "agent-usable" | "for-humans" | "parked" | "redirect" | "wrong-industry" | "dead",
    "confidence": "high" | "medium" | "low",
    "reason": "Brief explanation (1-2 sentences)",
    "name": "Suggested display name for the site",
    "description": "Brief description of what the site does (1 sentence)",
    "category": "social" | "creative" | "platform" | "gaming"
}}
"""


def load_cache() -> dict:
    """Load verification cache."""
    if VERIFICATION_CACHE.exists():
        with open(VERIFICATION_CACHE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    """Save verification cache."""
    with open(VERIFICATION_CACHE, 'w') as f:
        json.dump(cache, f, indent=2)


def load_excluded() -> dict:
    """Load excluded domains."""
    if EXCLUDED_JSON.exists():
        with open(EXCLUDED_JSON) as f:
            data = json.load(f)
            return data.get('excluded', {})
    return {}


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


async def fetch_site(url: str, session: aiohttp.ClientSession) -> dict:
    """Fetch a site and extract content."""
    result = {
        'url': url,
        'title': '',
        'content': '',
        'status': None,
        'redirect': None,
        'error': None
    }

    try:
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=15),
            ssl=ssl_ctx,
            allow_redirects=True,
            max_redirects=5
        ) as response:
            result['status'] = response.status

            # Check for redirect to different domain
            final_url = str(response.url)
            original_domain = urlparse(url).netloc.replace('www.', '')
            final_domain = urlparse(final_url).netloc.replace('www.', '')

            if original_domain != final_domain:
                result['redirect'] = final_url

            if response.status == 200:
                html = await response.text()

                # Extract title
                import re
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                if title_match:
                    result['title'] = title_match.group(1).strip()[:200]

                # Extract text content (simplified)
                # Remove scripts and styles
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<[^>]+>', ' ', html)
                html = re.sub(r'\s+', ' ', html)

                result['content'] = html.strip()[:3000]  # Limit content size

    except asyncio.TimeoutError:
        result['error'] = 'timeout'
    except aiohttp.ClientError as e:
        result['error'] = str(e)[:100]
    except Exception as e:
        result['error'] = str(e)[:100]

    return result


def verify_with_llm(client: anthropic.Anthropic, site_data: dict) -> dict:
    """Verify a site using Claude."""

    # Handle redirects
    if site_data.get('redirect'):
        return {
            'verdict': 'redirect',
            'confidence': 'high',
            'reason': f"Redirects to {site_data['redirect']}",
            'name': '',
            'description': '',
            'category': 'platform'
        }

    # Handle errors
    if site_data.get('error'):
        return {
            'verdict': 'dead',
            'confidence': 'high',
            'reason': f"Could not fetch: {site_data['error']}",
            'name': '',
            'description': '',
            'category': 'platform'
        }

    # Handle non-200 responses
    if site_data.get('status') != 200:
        return {
            'verdict': 'dead',
            'confidence': 'high',
            'reason': f"HTTP status {site_data['status']}",
            'name': '',
            'description': '',
            'category': 'platform'
        }

    # Minimal content check
    if len(site_data.get('content', '')) < 50:
        return {
            'verdict': 'parked',
            'confidence': 'medium',
            'reason': 'Minimal or no content',
            'name': '',
            'description': '',
            'category': 'platform'
        }

    # Build prompt
    prompt = VERIFICATION_PROMPT.format(
        url=site_data['url'],
        title=site_data.get('title', 'Unknown'),
        content=site_data.get('content', '')[:2500]
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        text = response.content[0].text.strip()
        # Remove markdown code blocks if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            text = text.rsplit('```', 1)[0]

        result = json.loads(text)
        return result

    except json.JSONDecodeError as e:
        return {
            'verdict': 'error',
            'confidence': 'low',
            'reason': f'Failed to parse LLM response: {str(e)[:50]}',
            'name': '',
            'description': '',
            'category': 'platform'
        }
    except Exception as e:
        return {
            'verdict': 'error',
            'confidence': 'low',
            'reason': f'LLM error: {str(e)[:50]}',
            'name': '',
            'description': '',
            'category': 'platform'
        }


def get_unverified_sites() -> list:
    """Get sites from crawler DB that aren't in portals or exclusions."""
    if not CRAWLER_DB.exists():
        return []

    with open(CRAWLER_DB) as f:
        db = json.load(f)

    sites = db.get('sites', {})
    existing_portals = load_portals()
    excluded = load_excluded()
    cache = load_cache()

    unverified = []
    for url, info in sites.items():
        if not info.get('alive') or not info.get('has_real_content'):
            continue

        domain = urlparse(url if url.startswith('http') else f'https://{url}').netloc.replace('www.', '')

        # Skip if already in portals
        if domain in existing_portals:
            continue

        # Skip if excluded
        if domain in excluded:
            continue

        # Skip if recently verified in cache
        if domain in cache:
            verified_date = cache[domain].get('verified', '')
            if verified_date >= (datetime.now().strftime('%Y-%m-01')):  # This month
                continue

        unverified.append({
            'url': info.get('url', f'https://{domain}'),
            'domain': domain,
            'title': info.get('title', '')
        })

    return unverified


async def verify_sites(urls: list) -> dict:
    """Verify a list of sites."""
    client = anthropic.Anthropic()
    cache = load_cache()
    results = {'agent-usable': [], 'excluded': [], 'errors': []}

    async with aiohttp.ClientSession() as session:
        for i, item in enumerate(urls):
            if isinstance(item, str):
                url = item if item.startswith('http') else f'https://{item}'
                domain = urlparse(url).netloc.replace('www.', '')
            else:
                url = item['url']
                domain = item['domain']

            print(f"\n[{i+1}/{len(urls)}] Verifying {domain}...")

            # Fetch site
            site_data = await fetch_site(url, session)

            # Verify with LLM
            verification = verify_with_llm(client, site_data)

            # Store in cache
            cache[domain] = {
                'verified': datetime.now().strftime('%Y-%m-%d'),
                'result': verification
            }

            # Classify result
            verdict = verification.get('verdict', 'error')
            confidence = verification.get('confidence', 'low')
            reason = verification.get('reason', 'Unknown')

            if verdict == 'agent-usable':
                icon = '✅'
                results['agent-usable'].append({
                    'domain': domain,
                    'url': url,
                    'name': verification.get('name', domain),
                    'description': verification.get('description', ''),
                    'category': verification.get('category', 'platform'),
                    'confidence': confidence
                })
            elif verdict in ['for-humans', 'parked', 'redirect', 'wrong-industry', 'dead']:
                icon = '❌'
                results['excluded'].append({
                    'domain': domain,
                    'verdict': verdict,
                    'reason': reason
                })
            else:
                icon = '⚠️'
                results['errors'].append({
                    'domain': domain,
                    'reason': reason
                })

            print(f"  {icon} {verdict} ({confidence}): {reason[:60]}")

            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)

    # Save cache
    save_cache(cache)

    return results


def apply_results(results: dict):
    """Apply verification results to portals and exclusions."""

    # Add agent-usable sites to portals
    if results['agent-usable']:
        with open(PORTALS_JSON) as f:
            portals_data = json.load(f)

        existing_domains = {
            urlparse(p['url']).netloc.replace('www.', '')
            for p in portals_data['portals']
        }

        added = 0
        for site in results['agent-usable']:
            if site['domain'] not in existing_domains:
                portal = {
                    'id': site['domain'].replace('.', '-'),
                    'name': site['name'],
                    'url': site['url'],
                    'icon': '🦞' if any(k in site['domain'] for k in ['molt', 'claw', 'lob']) else '🤖',
                    'category': site['category'],
                    'tag': 'Agent Platform',
                    'description': site['description'],
                    'discovered': datetime.now().strftime('%Y-%m-%d'),
                    'relevance': 80,
                    'trust': 'high' if site['confidence'] == 'high' else 'medium'
                }
                portals_data['portals'].append(portal)
                added += 1
                print(f"  + Added {site['domain']} to portals")

        if added:
            with open(PORTALS_JSON, 'w') as f:
                json.dump(portals_data, f, indent=2)
            print(f"\n✅ Added {added} sites to portals.json")

    # Add excluded sites
    if results['excluded']:
        with open(EXCLUDED_JSON) as f:
            excluded_data = json.load(f)

        excluded = excluded_data.get('excluded', {})
        added = 0

        for site in results['excluded']:
            if site['domain'] not in excluded:
                excluded[site['domain']] = {
                    'reason': site['reason'],
                    'category': site['verdict'],
                    'checked': datetime.now().strftime('%Y-%m-%d'),
                    'recheck_after': datetime.now().strftime('%Y-%m-%d').replace(
                        datetime.now().strftime('%m'),
                        str((int(datetime.now().strftime('%m')) + 6 - 1) % 12 + 1).zfill(2)
                    )
                }
                added += 1
                print(f"  - Excluded {site['domain']}: {site['reason'][:40]}")

        if added:
            excluded_data['excluded'] = excluded
            with open(EXCLUDED_JSON, 'w') as f:
                json.dump(excluded_data, f, indent=2)
            print(f"\n❌ Added {added} sites to exclusions")


def main():
    parser = argparse.ArgumentParser(description='LLM-powered site verification')
    parser.add_argument('--url', help='Verify a single URL')
    parser.add_argument('--batch', help='File with URLs to verify (one per line)')
    parser.add_argument('--recheck', action='store_true', help='Re-verify sites due for recheck')
    parser.add_argument('--apply', action='store_true', help='Auto-apply results to portals/exclusions')
    parser.add_argument('--limit', type=int, default=20, help='Max sites to verify (default: 20)')
    args = parser.parse_args()

    print("🔍 MOLT SITE VERIFICATION (LLM-powered)\n")

    # Determine what to verify
    urls = []

    if args.url:
        urls = [args.url]
    elif args.batch:
        with open(args.batch) as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        # Get unverified sites from crawler
        unverified = get_unverified_sites()
        if not unverified:
            print("No unverified sites found. Run the crawler first or use --url/--batch.")
            return
        urls = unverified[:args.limit]
        print(f"Found {len(unverified)} unverified sites, checking first {len(urls)}...")

    # Run verification
    results = asyncio.run(verify_sites(urls))

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"✅ Agent-usable: {len(results['agent-usable'])}")
    print(f"❌ Excluded: {len(results['excluded'])}")
    print(f"⚠️  Errors: {len(results['errors'])}")

    if results['agent-usable']:
        print("\nAgent-usable sites:")
        for site in results['agent-usable']:
            print(f"  • {site['domain']}: {site['description'][:50]}")

    # Apply results if requested
    if args.apply and (results['agent-usable'] or results['excluded']):
        print("\nApplying results...")
        apply_results(results)
    elif results['agent-usable'] or results['excluded']:
        print("\nRun with --apply to add these to portals/exclusions")


if __name__ == "__main__":
    main()
