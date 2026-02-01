#!/usr/bin/env python3
"""
Molt Ecosystem Crawler - PARALLEL MODE
Finds ALL molt-related websites with REAL content.
Uses parallel DNS and HTTP checks for speed.
"""

import asyncio
import aiohttp
import ssl
import certifi
import json
import re
import socket
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

DB_FILE = Path(__file__).parent / "molt_sites_db.json"

# All known seeds - comprehensive list from ecosystem mapping
SEED_URLS = [
    # Index/Directory
    "https://agentsy.live",
    "https://claw.direct",
    "https://clawcrunch.com",

    # Social Networks
    "https://moltbook.com",
    "https://moltbook.space",
    "https://moltx.io",
    "https://clawk.ai",
    "https://clawcaster.xyz",

    # Forums/Imageboards
    "https://4claw.org",
    "https://lobchan.ai",
    "https://moltoverflow.com",

    # Creative/Media
    "https://instaclaw.xyz",
    "https://clawnhub.com",
    "https://molt-place.com",

    # Dating/Social
    "https://shellmates.app",
    "https://clawdr.app",

    # Messaging
    "https://moltline.app",

    # Work/Markets
    "https://openwork.bot",
    "https://clawnet.org",
    "https://moltroad.com",
    "https://clawdslist.org",
    "https://moltcities.org",
    "https://aegisagent.ai",

    # Token/DeFi
    "https://bankr.bot",
    "https://clanker.world",
    "https://clawnch.bot",
    "https://moltlaunch.com",

    # Prediction Markets
    "https://clawarena.ai",
    "https://polyclaw.ai",

    # Gaming
    "https://molt.chess",
    "https://moltiplayer.com",
    "https://clawcity.app",

    # Virtual Worlds
    "https://shell-town.com",

    # Infrastructure
    "https://openclaw.ai",
    "https://starkbot.ai",
    "https://clawhub.ai",
    "https://clawhunt.app",

    # News/Content
    "https://clawnews.io",
    "https://crabernews.com",

    # Community
    "https://molt.church",
    "https://shipyard.bot",
    "https://aethernet.world",
    "https://a2a-protocol.org",
    "https://warpcast.com",
]

# Keywords that indicate molt/agent ecosystem
KEYWORDS = ['molt', 'claw', 'lobster', 'crab', 'crustacean', 'shell', 'exo', 'agent', 'agentic', 'bot', 'autonomous']

# Skip mainstream sites
SKIP = {
    'google.com', 'facebook.com', 'twitter.com', 'x.com', 'github.com',
    'youtube.com', 'linkedin.com', 'instagram.com', 'reddit.com',
    'discord.com', 'telegram.org', 'medium.com', 'substack.com',
    'notion.so', 'vercel.app', 'netlify.app', 'cloudflare.com',
    'tailwindcss.com', 'unpkg.com', 'jsdelivr.net', 'googleapis.com',
    'gstatic.com', 'w3.org', 'schema.org', 'apple.com', 'microsoft.com',
}

# Parked domain indicators
PARKED_INDICATORS = [
    'buy this domain', 'domain is for sale', 'domain for sale',
    'parked', 'for sale', 'purchase this domain', 'make an offer',
    'hugedomains', 'godaddy', 'namecheap', 'dan.com', 'sedo.com',
    'afternic', 'domainmarket', 'brandbucket', 'squadhelp',
    'domain available', 'inquire about', 'sponsored listings',
]

# Domain patterns - expanded based on ecosystem mapping
TLDS = ['com', 'io', 'ai', 'app', 'xyz', 'live', 'world', 'org', 'net', 'co', 'dev', 'bot', 'gg', 'space', 'direct', 'chess', 'town']
BASES = ['molt', 'claw', 'agent', 'lobster', 'shell', 'bot', 'crab', 'open', 'stark', 'bankr', 'poly']
SUFFIXES = ['', 's', 'hub', 'net', 'verse', 'world', 'book', 'chan', 'news', 'list', 'hunt', 'work', 'city', 'road', 'base',
            'overflow', 'arena', 'crunch', 'caster', 'line', 'mates', 'dr', 'launch', 'nch', 'place', 'x', 'direct']


class Database:
    def __init__(self):
        self.path = DB_FILE
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path) as f:
                    return json.load(f)
            except:
                pass
        return {"created": datetime.now().isoformat(), "sites": {}}

    def save(self):
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=2)
        real = [d for d, info in self.data["sites"].items() if info.get("has_content")]
        print(f"\n💾 Saved {len(self.data['sites'])} sites ({len(real)} with real content)")

    def add(self, domain, url, source, alive=True, has_content=False, title=""):
        is_new = domain not in self.data["sites"]
        if is_new:
            self.data["sites"][domain] = {
                "url": url, "source": source, "alive": alive,
                "has_content": has_content, "title": title,
                "first_seen": datetime.now().isoformat(),
            }
        else:
            self.data["sites"][domain]["alive"] = alive
            self.data["sites"][domain]["has_content"] = has_content
            if title:
                self.data["sites"][domain]["title"] = title
        return is_new

    def known(self):
        return set(self.data["sites"].keys())


class Crawler:
    def __init__(self, db: Database):
        self.db = db
        self.visited = set()
        self.discoveries = []
        self.sem = asyncio.Semaphore(500)  # MAX concurrency
        self.dns_executor = ThreadPoolExecutor(max_workers=200)

    def normalize(self, url):
        try:
            p = urlparse(url if '://' in url else f'https://{url}')
            d = p.netloc.lower()
            return d[4:] if d.startswith('www.') else d
        except:
            return ""

    def is_interesting(self, domain):
        d = domain.lower()
        if any(s in d for s in SKIP):
            return False
        return any(k in d for k in KEYWORDS)

    def is_parked(self, html):
        if not html or len(html) < 500:
            return True
        html_lower = html.lower()
        parked_count = sum(1 for p in PARKED_INDICATORS if p in html_lower)
        if parked_count >= 2:
            return True
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            text = soup.get_text(separator=' ', strip=True)
            if len(text) < 200 or len(text.split()) < 30:
                return True
        except:
            pass
        return parked_count >= 1 and len(html) < 5000

    def get_title(self, html):
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.find('title')
            if title:
                return title.get_text(strip=True)[:100]
        except:
            pass
        return ""

    async def fetch(self, session, url):
        async with self.sem:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8), allow_redirects=True) as r:
                    if r.status == 200:
                        return await r.text(), True
                    return None, r.status < 500
            except:
                return None, False

    def extract_domains(self, html, base_url):
        domains = set()
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = str(a.get('href', ''))
                full = urljoin(base_url, href)
                d = self.normalize(full)
                if d:
                    domains.add(d)
            for m in re.finditer(r'https?://([a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,})', str(soup)):
                domains.add(m.group(1).lower())
        except:
            pass
        return domains

    def dns_check_sync(self, domain):
        """Synchronous DNS check for thread pool."""
        try:
            socket.setdefaulttimeout(2)
            socket.gethostbyname(domain)
            return domain, True
        except:
            return domain, False

    async def batch_dns_check(self, domains):
        """Check many domains in parallel using thread pool."""
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(self.dns_executor, self.dns_check_sync, d) for d in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        alive = []
        for r in results:
            if isinstance(r, tuple) and r[1]:
                alive.append(r[0])
        return alive

    async def batch_check_sites(self, session, domains, source):
        """Check multiple domains for real content in parallel."""
        async def check_one(domain):
            if domain in self.visited:
                return None
            self.visited.add(domain)

            url = f"https://{domain}"
            html, alive = await self.fetch(session, url)

            if not alive:
                return None

            has_content = html and not self.is_parked(html)
            title = self.get_title(html) if html else ""

            is_new = self.db.add(domain, url, source, True, has_content, title)

            if has_content:
                if is_new:
                    self.discoveries.append(domain)
                return (domain, title, True)
            return (domain, "", False)

        tasks = [check_one(d) for d in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, tuple):
                domain, title, has_content = r
                status = "✅" if has_content else "⚪"
                if has_content:
                    print(f"  {status} {domain}" + (f" - {title[:40]}" if title else ""))

    async def crawl(self, session, url, depth=0):
        domain = self.normalize(url)
        if not domain or domain in self.visited:
            return
        self.visited.add(domain)

        html, alive = await self.fetch(session, url)

        has_content = False
        title = ""
        if html:
            has_content = not self.is_parked(html)
            title = self.get_title(html)

        status = "✅" if has_content else "⚪" if alive else "❌"
        print(f"  {status} {domain}" + (f" - {title[:40]}" if title and has_content else ""))

        is_new = self.db.add(domain, url, "crawl", alive, has_content, title)
        if is_new and has_content:
            self.discoveries.append(domain)

        if html and has_content and depth < 2:
            new_domains = [d for d in self.extract_domains(html, url)
                          if d not in self.visited and self.is_interesting(d)]
            if new_domains:
                await self.batch_check_sites(session, new_domains[:20], "link")

    async def run(self):
        print("\n" + "="*60)
        print("🦞 MOLT CRAWLER - PARALLEL MODE")
        print("="*60)
        print(f"✅ = real content | ⚪ = parked/empty | ❌ = down")

        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        conn = aiohttp.TCPConnector(limit=500, ssl=ssl_ctx, ttl_dns_cache=300)

        async with aiohttp.ClientSession(connector=conn) as session:
            # Phase 1: Crawl seeds
            print(f"\n📡 PHASE 1: CRAWLING {len(SEED_URLS)} SEEDS")
            print("-"*40)
            tasks = [self.crawl(session, url, 0) for url in SEED_URLS]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Phase 2: Generate candidates
            print(f"\n🔨 PHASE 2: DOMAIN ENUMERATION")
            print("-"*40)
            candidates = set()
            for base in BASES:
                for suffix in SUFFIXES:
                    for tld in TLDS:
                        d = f"{base}{suffix}.{tld}"
                        if d not in self.db.known() and d not in self.visited:
                            candidates.add(d)

            print(f"  Generated {len(candidates)} candidates")
            print(f"  Running parallel DNS checks...")

            # Batch DNS check (very fast)
            candidates_list = list(candidates)
            batch_size = 500
            all_alive = []

            for i in range(0, len(candidates_list), batch_size):
                batch = candidates_list[i:i+batch_size]
                alive = await self.batch_dns_check(batch)
                all_alive.extend(alive)
                print(f"    DNS batch {i//batch_size + 1}: {len(alive)} alive domains")

            print(f"  Found {len(all_alive)} domains with DNS")
            print(f"  Checking for real content...")

            # Batch HTTP check
            for i in range(0, len(all_alive), 100):
                batch = all_alive[i:i+100]
                await self.batch_check_sites(session, batch, "bruteforce")

        self.db.save()

        print("\n" + "="*60)
        print("📊 RESULTS")
        print("="*60)
        print(f"New real sites found: {len(self.discoveries)}")
        print(f"Total in database: {len(self.db.known())}")

        if self.discoveries:
            print(f"\n✅ NEW REAL SITES:")
            for d in sorted(self.discoveries):
                info = self.db.data["sites"].get(d, {})
                title = info.get("title", "")[:50]
                print(f"   • https://{d}" + (f" - {title}" if title else ""))

        return self.discoveries


async def main():
    db = Database()
    crawler = Crawler(db)
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
