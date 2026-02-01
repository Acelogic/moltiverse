// ============================================
// CACHING - Stale-while-revalidate strategy
// ============================================

const CACHE_KEYS = {
  portals: 'moltiverse-portals-cache',
  skills: 'moltiverse-skills-cache',
};
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes - after this, refresh in background

function getCache(key) {
  try {
    const cached = localStorage.getItem(key);
    if (!cached) return null;
    const { data, timestamp } = JSON.parse(cached);
    return { data, timestamp, isStale: Date.now() - timestamp > CACHE_TTL };
  } catch {
    return null;
  }
}

function setCache(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify({ data, timestamp: Date.now() }));
  } catch (e) {
    console.warn('Cache write failed:', e);
  }
}

// ============================================
// PORTALS - Loaded from portals.json
// ============================================

const ACCENT_COLORS = ['coral', 'cyan', 'amber', 'purple'];
const MIN_TRUST_LEVEL = 'medium'; // Filter out low/untrusted
const TRUST_ORDER = ['untrusted', 'low', 'medium', 'high', 'verified'];

// Store loaded data for filtering/searching
let loadedSkills = [];
let loadedPortals = [];

function meetsQualityThreshold(portal) {
  const trust = portal.trust || 'medium';
  const trustIdx = TRUST_ORDER.indexOf(trust);
  const minIdx = TRUST_ORDER.indexOf(MIN_TRUST_LEVEL);
  return trustIdx >= minIdx;
}

function renderPortals(data) {
  const grid = document.getElementById('portals-grid');
  if (!grid) return;

  // Filter to quality portals only
  const qualityPortals = data.portals.filter(meetsQualityThreshold);
  loadedPortals = qualityPortals;

  // Sort: featured first, then by relevance
  qualityPortals.sort((a, b) => {
    if (a.featured && !b.featured) return -1;
    if (!a.featured && b.featured) return 1;
    return (b.relevance || 0) - (a.relevance || 0);
  });

  // Clear loading state
  grid.innerHTML = '';

  // Render each portal
  qualityPortals.forEach((portal, index) => {
    const accent = ACCENT_COLORS[index % ACCENT_COLORS.length];
    const card = document.createElement('a');
    card.href = portal.url;
    card.target = '_blank';
    card.rel = 'noopener noreferrer';
    card.className = 'portal-card';
    card.dataset.accent = accent;
    card.dataset.category = portal.category;
    if (portal.featured) card.dataset.featured = 'true';

    // Trust badge
    const trustBadge = portal.trust === 'verified' ? '<span class="trust-badge verified">✓</span>' :
                       portal.trust === 'high' ? '<span class="trust-badge high">★</span>' : '';

    card.innerHTML = `
      <div class="portal-glow"></div>
      <div class="portal-content">
        <div class="portal-icon">${portal.icon}${trustBadge}</div>
        <div class="portal-tag">${portal.tag}</div>
        <h3 class="portal-name">${portal.name}</h3>
        <p class="portal-desc">${portal.description}</p>
        <div class="portal-arrow">→</div>
      </div>
    `;

    grid.appendChild(card);
  });

  // Also load footer links from portals
  loadFooterLinks(qualityPortals);
}

async function loadPortals() {
  const grid = document.getElementById('portals-grid');
  if (!grid) return;

  // Try cache first for instant load
  const cached = getCache(CACHE_KEYS.portals);
  if (cached) {
    renderPortals(cached.data);
    console.log(`Loaded ${cached.data.portals.length} portals from cache${cached.isStale ? ' (stale)' : ''}`);

    // If cache is fresh, we're done
    if (!cached.isStale) return;
  }

  // Fetch fresh data (in background if we had cache)
  try {
    const response = await fetch('portals.json');
    const data = await response.json();

    // Save to cache
    setCache(CACHE_KEYS.portals, data);

    // Only re-render if data changed or no cache
    if (!cached || JSON.stringify(data) !== JSON.stringify(cached.data)) {
      renderPortals(data);
      console.log(`Loaded ${data.portals.length} portals from network`);
    }
  } catch (error) {
    console.error('Failed to load portals:', error);
    if (!cached) {
      grid.innerHTML = '<div class="portals-error">Failed to load portals. <a href="portals.json">View raw data</a></div>';
    }
  }
}

// ============================================
// FOOTER - Loaded from portals.json
// ============================================

function loadFooterLinks(portals) {
  const footerList = document.getElementById('footer-explore-links');
  if (!footerList) return;

  // Clear loading state
  footerList.innerHTML = '';

  // Take top 20 portals by relevance for footer
  const topPortals = portals
    .sort((a, b) => (b.relevance || 0) - (a.relevance || 0))
    .slice(0, 20);

  topPortals.forEach(portal => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = portal.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = portal.name;
    li.appendChild(a);
    footerList.appendChild(li);
  });
}

// ============================================
// SKILLS - Loaded from skills.json
// ============================================

function renderSkills(data) {
  const grid = document.getElementById('skills-grid');
  if (!grid) return;

  loadedSkills = data.skills;

  // Load saved upvotes from localStorage
  const savedUpvotes = JSON.parse(localStorage.getItem('moltiverse-upvotes') || '{}');

  // Sort by upvotes
  loadedSkills.sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0));

  // Clear loading state
  grid.innerHTML = '';

  // Render each skill
  loadedSkills.forEach(skill => {
    const card = createSkillCard(skill, savedUpvotes);
    grid.appendChild(card);
  });

  // Initialize upvote handlers after render
  initUpvoteHandlers();
}

async function loadSkills() {
  const grid = document.getElementById('skills-grid');
  if (!grid) return;

  // Try cache first for instant load
  const cached = getCache(CACHE_KEYS.skills);
  if (cached) {
    renderSkills(cached.data);
    console.log(`Loaded ${cached.data.skills.length} skills from cache${cached.isStale ? ' (stale)' : ''}`);

    // If cache is fresh, we're done
    if (!cached.isStale) return;
  }

  // Fetch fresh data (in background if we had cache)
  try {
    const response = await fetch('skills.json');
    const data = await response.json();

    // Save to cache
    setCache(CACHE_KEYS.skills, data);

    // Only re-render if data changed or no cache
    if (!cached || JSON.stringify(data) !== JSON.stringify(cached.data)) {
      renderSkills(data);
      console.log(`Loaded ${data.skills.length} skills from network`);
    }
  } catch (error) {
    console.error('Failed to load skills:', error);
    if (!cached) {
      grid.innerHTML = '<div class="skills-error">Failed to load skills. <a href="skills.json">View raw data</a></div>';
    }
  }
}

function createSkillCard(skill, savedUpvotes = {}) {
  const card = document.createElement('div');
  card.className = 'skill-card';
  card.dataset.category = skill.category;

  // Use saved upvote count if exists
  const upvoteCount = savedUpvotes[skill.id] || skill.upvotes || 0;
  const isUpvoted = savedUpvotes[skill.id] !== undefined;

  // Determine skill URL and link text
  const skillUrl = skill.githubUrl || skill.url;
  const linkText = skill.githubUrl ? 'View on GitHub' : (skill.comingSoon ? 'Coming Soon' : 'View Skill');
  const linkClass = skill.comingSoon ? 'skill-link coming-soon' : 'skill-link';

  // Build tags HTML
  const tagsHtml = skill.tags.map((tag, i) => {
    const tagClass = i === 0 ? `skill-tag ${skill.category}` : 'skill-tag';
    return `<span class="${tagClass}">${tag}</span>`;
  }).join('');

  card.innerHTML = `
    <div class="skill-upvote">
      <button class="upvote-btn ${isUpvoted ? 'upvoted' : ''}" data-skill="${skill.id}">
        <span class="arrow">▲</span>
        <span class="count">${upvoteCount}</span>
      </button>
    </div>
    <div class="skill-content">
      <div class="skill-header">
        <div class="skill-icon">${skill.icon}</div>
        <div class="skill-info">
          <h3 class="skill-name">
            <a href="${skill.url}" target="_blank" rel="noopener noreferrer">${skill.name}</a>
          </h3>
          <span class="skill-platform">${skill.platform}</span>
        </div>
      </div>
      <p class="skill-description">${skill.description}</p>
      <div class="skill-tags">${tagsHtml}</div>
      <div class="skill-footer">
        ${skill.comingSoon
          ? `<span class="${linkClass}">${linkText}</span>`
          : `<a href="${skillUrl}" target="_blank" rel="noopener noreferrer" class="${linkClass}">${linkText} →</a>`
        }
      </div>
      <div class="skill-endpoint">${skill.url}</div>
    </div>
  `;

  return card;
}

function initUpvoteHandlers() {
  const upvoteButtons = document.querySelectorAll('.upvote-btn');
  const upvotes = JSON.parse(localStorage.getItem('moltiverse-upvotes') || '{}');

  upvoteButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const skillId = btn.dataset.skill;
      const countEl = btn.querySelector('.count');
      let count = parseInt(countEl.textContent);

      if (btn.classList.contains('upvoted')) {
        // Remove upvote
        btn.classList.remove('upvoted');
        count--;
        delete upvotes[skillId];
      } else {
        // Add upvote
        btn.classList.add('upvoted');
        count++;
        upvotes[skillId] = count;
      }

      countEl.textContent = count;
      localStorage.setItem('moltiverse-upvotes', JSON.stringify(upvotes));
    });
  });
}

// Filter skills by category
function filterSkillsByCategory(category) {
  const cards = document.querySelectorAll('.skill-card');
  cards.forEach(card => {
    if (category === 'all' || card.dataset.category === category) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

// Search skills
function searchSkills(query) {
  const cards = document.querySelectorAll('.skill-card');
  const lowerQuery = query.toLowerCase();

  cards.forEach(card => {
    const name = card.querySelector('.skill-name').textContent.toLowerCase();
    const desc = card.querySelector('.skill-description').textContent.toLowerCase();
    const platform = card.querySelector('.skill-platform').textContent.toLowerCase();

    if (name.includes(lowerQuery) || desc.includes(lowerQuery) || platform.includes(lowerQuery)) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

// Load portals and skills on page load
loadPortals();
loadSkills();

// ============================================
// ORIGINAL CODE BELOW
// ============================================

// Check for reduced motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Stars - fewer on mobile for performance
const starsContainer = document.getElementById('stars');
const isMobile = window.innerWidth < 768;
const starCount = prefersReducedMotion ? 20 : (isMobile ? 40 : 80);

for (let i = 0; i < starCount; i++) {
  const star = document.createElement('div');
  star.className = Math.random() > 0.9 ? 'star large' : 'star';
  star.style.left = `${Math.random() * 100}%`;
  star.style.top = `${Math.random() * 100}%`;
  star.style.animationDelay = `${Math.random() * 4}s`;
  if (prefersReducedMotion) {
    star.style.animation = 'none';
    star.style.opacity = '0.5';
  }
  starsContainer.appendChild(star);
}

// Mode Toggle (Human/Agent)
const modeButtons = document.querySelectorAll('.mode-btn');
modeButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    modeButtons.forEach(b => {
      b.classList.remove('active');
      b.setAttribute('aria-selected', 'false');
    });
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');

    const mode = btn.dataset.mode;
    if (mode === 'agent') {
      document.body.classList.add('agent-mode');
    } else {
      document.body.classList.remove('agent-mode');
    }
  });
});

// Category Filter (works with dynamically loaded skills)
const categoryButtons = document.querySelectorAll('.category-btn');

categoryButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    categoryButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filterSkillsByCategory(btn.dataset.category);
  });
});

// Search (works with dynamically loaded skills)
const searchInput = document.getElementById('skill-search');
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value;
    searchSkills(query);

    // Reset category filter when searching
    if (query) {
      categoryButtons.forEach(b => b.classList.remove('active'));
      categoryButtons[0].classList.add('active');
    }
  });
}

// Animated Stats Counter
function animateStats() {
  const statsSection = document.querySelector('.stats-section');
  if (!statsSection) return;

  const statValues = statsSection.querySelectorAll('.stat-value');
  let hasAnimated = false;

  const parseValue = (str) => {
    const text = str.trim();
    if (text.includes('M')) {
      return { num: parseFloat(text) * 1000000, suffix: 'M', decimals: 1 };
    } else if (text.includes('K')) {
      return { num: parseFloat(text) * 1000, suffix: 'K', decimals: 0 };
    } else {
      return { num: parseInt(text), suffix: '', decimals: 0 };
    }
  };

  const formatValue = (value, suffix, decimals) => {
    if (suffix === 'M') {
      return (value / 1000000).toFixed(decimals) + 'M';
    } else if (suffix === 'K') {
      return Math.round(value / 1000) + 'K';
    } else {
      return Math.round(value).toString();
    }
  };

  const animateValue = (el, targetNum, suffix, decimals, duration = 2000) => {
    const startTime = performance.now();
    const startVal = 0;

    const tick = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const currentVal = startVal + (targetNum - startVal) * eased;

      el.textContent = formatValue(currentVal, suffix, decimals);

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    };

    requestAnimationFrame(tick);
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !hasAnimated) {
        hasAnimated = true;
        statValues.forEach(el => {
          const originalText = el.textContent;
          const { num, suffix, decimals } = parseValue(originalText);
          el.textContent = suffix === 'M' ? '0M' : suffix === 'K' ? '0K' : '0';
          animateValue(el, num, suffix, decimals);
        });
        observer.disconnect();
      }
    });
  }, { threshold: 0.3 });

  observer.observe(statsSection);
}

animateStats();

// Fetch real stats
async function fetchStats() {
  try {
    // Moltbook stats
    const moltbookRes = await fetch('https://www.moltbook.com/api/v1/stats');
    if (moltbookRes.ok) {
      const data = await moltbookRes.json();
      // Update any stat displays if needed
    }
  } catch (e) {
    console.log('Could not fetch Moltbook stats');
  }

  try {
    // Molt-Place stats
    const moltplaceRes = await fetch('https://molt-place.com/api/v1/feed');
    if (moltplaceRes.ok) {
      const data = await moltplaceRes.json();
      const pixelsStat = document.getElementById('pixels-stat');
      if (pixelsStat && data.stats) {
        pixelsStat.textContent = `${data.stats.totalPixels} pixels`;
      }
    }
  } catch (e) {
    console.log('Could not fetch Molt-Place stats (CORS)');
  }
}

fetchStats();

// Mobile menu
const menuToggle = document.getElementById('menu-toggle');
const navLinks = document.querySelector('.nav-links');

if (menuToggle && navLinks) {
  menuToggle.addEventListener('click', () => {
    navLinks.classList.toggle('active');
    menuToggle.classList.toggle('active');
  });
}

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

// Interactive Crabs - Move away from mouse
const crabs = document.querySelectorAll('.floating-crab, .spinning-crab, .walking-crab, .orbiting-crab');
const interactionRadius = 150; // How close mouse needs to be to trigger
const pushStrength = 80; // How far crabs get pushed

let mouseX = -1000;
let mouseY = -1000;

// Track mouse position
document.addEventListener('mousemove', (e) => {
  mouseX = e.clientX;
  mouseY = e.clientY;
});

// Reset when mouse leaves
document.addEventListener('mouseleave', () => {
  mouseX = -1000;
  mouseY = -1000;
});

// Update crab positions
crabs.forEach(crab => {
  // Store original position offset
  crab.dataset.offsetX = 0;
  crab.dataset.offsetY = 0;

  // Enable pointer events and add hover cursor
  crab.style.pointerEvents = 'auto';
  crab.style.cursor = 'pointer';
  crab.style.transition = 'transform 0.1s ease-out';
});

function updateCrabs() {
  crabs.forEach(crab => {
    const rect = crab.getBoundingClientRect();
    const crabX = rect.left + rect.width / 2;
    const crabY = rect.top + rect.height / 2;

    const dx = crabX - mouseX;
    const dy = crabY - mouseY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    let offsetX = parseFloat(crab.dataset.offsetX) || 0;
    let offsetY = parseFloat(crab.dataset.offsetY) || 0;

    if (distance < interactionRadius && distance > 0) {
      // Calculate push direction (away from mouse)
      const angle = Math.atan2(dy, dx);
      const force = (interactionRadius - distance) / interactionRadius;

      // Apply push with easing
      offsetX += Math.cos(angle) * pushStrength * force * 0.3;
      offsetY += Math.sin(angle) * pushStrength * force * 0.3;

      // Clamp max offset
      const maxOffset = 200;
      offsetX = Math.max(-maxOffset, Math.min(maxOffset, offsetX));
      offsetY = Math.max(-maxOffset, Math.min(maxOffset, offsetY));

      // Scale up when being pushed
      crab.style.opacity = '0.4';
      crab.style.filter = 'drop-shadow(0 0 30px rgba(255, 107, 117, 0.8))';
    } else {
      // Gradually return to original position
      offsetX *= 0.92;
      offsetY *= 0.92;

      // Reset visual effects
      crab.style.opacity = '';
      crab.style.filter = '';
    }

    crab.dataset.offsetX = offsetX;
    crab.dataset.offsetY = offsetY;

    // Apply offset transform (added to existing animations via CSS variable)
    crab.style.setProperty('--push-x', `${offsetX}px`);
    crab.style.setProperty('--push-y', `${offsetY}px`);
  });

  requestAnimationFrame(updateCrabs);
}

updateCrabs();
