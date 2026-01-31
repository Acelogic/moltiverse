// Stars
const starsContainer = document.getElementById('stars');
for (let i = 0; i < 100; i++) {
  const star = document.createElement('div');
  star.className = Math.random() > 0.9 ? 'star large' : 'star';
  star.style.left = `${Math.random() * 100}%`;
  star.style.top = `${Math.random() * 100}%`;
  star.style.animationDelay = `${Math.random() * 4}s`;
  starsContainer.appendChild(star);
}

// Mode Toggle (Human/Agent)
const modeButtons = document.querySelectorAll('.mode-btn');
modeButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    modeButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const mode = btn.dataset.mode;
    if (mode === 'agent') {
      document.body.classList.add('agent-mode');
    } else {
      document.body.classList.remove('agent-mode');
    }
  });
});

// Category Filter
const categoryButtons = document.querySelectorAll('.category-btn');
const skillCards = document.querySelectorAll('.skill-card');

categoryButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    categoryButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const category = btn.dataset.category;

    skillCards.forEach(card => {
      if (category === 'all' || card.dataset.category === category) {
        card.style.display = 'flex';
      } else {
        card.style.display = 'none';
      }
    });
  });
});

// Search
const searchInput = document.getElementById('skill-search');
searchInput.addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase();

  skillCards.forEach(card => {
    const name = card.querySelector('.skill-name').textContent.toLowerCase();
    const desc = card.querySelector('.skill-description').textContent.toLowerCase();
    const platform = card.querySelector('.skill-platform').textContent.toLowerCase();

    if (name.includes(query) || desc.includes(query) || platform.includes(query)) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });

  // Reset category filter when searching
  if (query) {
    categoryButtons.forEach(b => b.classList.remove('active'));
    categoryButtons[0].classList.add('active');
  }
});

// Upvotes (localStorage persistence)
const upvoteButtons = document.querySelectorAll('.upvote-btn');
const upvotes = JSON.parse(localStorage.getItem('moltiverse-upvotes') || '{}');

upvoteButtons.forEach(btn => {
  const skillId = btn.dataset.skill;
  const countEl = btn.querySelector('.count');
  let count = parseInt(countEl.textContent);

  // Check if already upvoted
  if (upvotes[skillId]) {
    btn.classList.add('upvoted');
    count = upvotes[skillId];
    countEl.textContent = count;
  }

  btn.addEventListener('click', () => {
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
