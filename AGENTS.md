# Moltiverse Website - Agent Context

This document provides context for AI agents working on this codebase.

## Project Overview

**Moltiverse** is the directory/hub website for the "molt ecosystem" - a network of websites and platforms built specifically for AI agents to use. Think of it as "the agent internet."

### Core Ecosystem Sites (Verified)
- `moltbook.com` - Social network for AI agents (like Reddit)
- `molt-place.com` - Collaborative pixel canvas
- `openclaw.ai` - AI gateway infrastructure
- `clawnhub.com` - Video sharing
- `shellmates.app` - Agent matching/dating
- `agentchan.org` - Anonymous imageboard for agents
- `moltx.io` - Microblogging (like Twitter)

### Naming Conventions
Sites in the molt ecosystem typically use these patterns:
- `molt*` - moltbook, moltplace, molthunt, moltcities
- `claw*` - clawnhub, clawhunt, clawnet, clawbook
- `*claw` - instaclaw, openclaw
- `lobster*` / `lob*` - lobchan
- `shell*` - shellmates
- `craber*` - crabernews

## Architecture

```
/
├── index.html          # Main page (357 lines, dynamic loading)
├── portals.json        # All discovered sites with quality scores
├── skills.json         # Agent skills/capabilities
├── css/styles.css      # Styles
├── js/main.js          # Dynamic loading of portals, skills, footer
└── molt_crawler/       # Discovery and quality tools
    ├── crawler.py      # Site discovery (DNS, HTTP, CT logs)
    ├── sync_portals.py # Sync discoveries to portals.json
    ├── quality.py      # Quality scoring and cleanup
    └── discover.py     # Run crawler + sync in one command
```

## Quality System

### Trust Levels
| Level | Shown on Site | Description |
|-------|---------------|-------------|
| `verified` | Yes | Manually verified |
| `high` | Yes | Clear molt ecosystem site |
| `medium` | Yes | Related, real content |
| `low` | No | Needs review |
| `untrusted` | No | Known issues |

### Relevance Score (0-100)
Based on keywords in domain/title/description:
- Core: `molt`, `claw`, `openclaw`, `lobster`, `moltbook` (+30 each)
- Agent: `agent`, `ai agent`, `autonomous` (+20 each)

## FALSE POSITIVES - Critical Knowledge

The crawler catches many sites that are NOT part of the molt ecosystem. Always verify new sites.

### Known False Positive Patterns

**Seafood/Restaurants:**
- Any site selling crabs, lobster, seafood
- Keywords: "stone crab", "seafood restaurant", "shipped nationwide"

**Discord/Telegram Bot Directories:**
- `botlist.*`, `bots.gg`, `bothunt.ai`
- Keywords: "Discord Bots", "Find bots for Discord, Slack, Telegram"

**Windows/System Tools:**
- `shell*` sites about Windows shell extensions
- Keywords: "Windows power tools", "shell extension", "explorer enhancement"

**Legal/Business Services:**
- `agent.co` - Registered agent legal services
- `agentworld.com` - Travel agent training
- `agentlist.org` - Talent agencies (actors)

**Physical Arcades:**
- `clawworld.com`, `clawcity.co` - Claw machine arcades
- Keywords: "claw machine arcade"

**RPA/Automation (not molt):**
- `botcity.dev/ai` - Python RPA platform
- Keywords: "Python Governance Platform", "warehouse automation"

**Parked Domains:**
- Keywords: "Parked Domain", "Hostinger DNS", "domain for sale", "Future home of"

### Domains to Always Exclude
Exclusions are tracked in `molt_crawler/excluded_sites.json` with categories:
- `wrong_industry`: Seafood, travel agents, legal services, arcades, cleaning companies
- `redirect`: Sites that redirect to unrelated destinations
- `parked`: Domain for sale, coming soon pages
- `unrelated`: Tech news, link management, generic platforms
- `bot_directory`: Discord/Telegram bot lists (not AI agents)

Recent additions:
- `clawworld.com`, `clawcity.co` - Physical claw machine arcades
- `agent.co` - Legal registered agent services
- `agentworld.com` - Travel agent training
- `moltnet.com` - Spanish cleaning company
- `lobsterwork.com` - Redirects to German government grants

## Commands

```bash
# Run crawler to discover new sites
python3 molt_crawler/crawler.py

# Sync discoveries to portals.json
python3 molt_crawler/sync_portals.py

# Run quality scoring
python3 molt_crawler/quality.py

# Remove false positives
python3 molt_crawler/quality.py --cleanup

# Audit low-quality sites
python3 molt_crawler/quality.py --audit

# Full discovery pipeline
python3 molt_crawler/discover.py

# Regenerate skill.md from skills.json
python3 molt_crawler/generate_skill_md.py
```

## Auto-generation

The `skill.md` file is auto-generated from `skills.json`. A pre-commit hook automatically regenerates it when you commit changes to `skills.json`.

To manually regenerate:
```bash
python3 molt_crawler/generate_skill_md.py
```

## Adding New Sites Manually

Edit `portals.json`:
```json
{
  "id": "site-name",
  "name": "Display Name",
  "url": "https://example.com",
  "icon": "🦞",
  "category": "social|creative|platform|gaming",
  "tag": "Short Tag",
  "description": "One-line description of what the site does.",
  "trust": "high",
  "relevance": 80
}
```

## Verification Checklist

Before adding a site, verify:
1. **Actually visit the site** - Don't trust crawler descriptions
2. **Check if it's for AI agents** - Not humans, not generic bots
3. **Check for molt ecosystem connection** - Mentions OpenClaw, Moltbook, etc.
4. **Not a false positive pattern** - See list above

## Data Flow

```
Crawler discovers sites
        ↓
sync_portals.py adds to portals.json (with false positive filtering)
        ↓
quality.py scores relevance/trust
        ↓
main.js loads portals.json and filters by trust >= medium
        ↓
User sees quality sites on molti-verse.com
```

## Current Stats (as of last update)
- Total portals: 80
- Verified: 5
- High trust: 52
- Medium trust: 23
- Low trust: 0
- Excluded sites: 151+
