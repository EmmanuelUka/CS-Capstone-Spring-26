<script setup>
import AppShellHeader from '../components/AppShellHeader.vue'
import MenuCard from '../components/MenuCard.vue'
import { homeMenuCards } from '../data/homeMenuCards'

defineProps({
  authBusy: {
    type: Boolean,
    default: false,
  },
  authLoading: {
    type: Boolean,
    default: false,
  },
  authStatus: {
    type: String,
    default: '',
  },
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
  user: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['login', 'logout', 'navigate'])

function handleCardSelect(cardId) {
  emit('navigate', cardId)
}
</script>

<template>
  <section class="home-page">
    <div class="page-shell">
      <AppShellHeader
        eyebrow="Hashmark Recruiting Assistant"
        title="A recruiting home screen that feels production-ready."
        description="The landing experience now acts like a real command center: clear session state, product modules with stronger hierarchy, and room to expand into deeper scouting workflows."
      />

      <div class="hero-grid">
        <section class="hero-panel">
          <p class="panel-label">Control Room</p>
          <h2>{{ isAuthenticated ? 'Session unlocked. Move into the board.' : 'Sign in, then open the board.' }}</h2>
          <p class="panel-copy">
            <template v-if="isAuthenticated">
              {{ user?.name || user?.email }} is cleared to move through the product from a single landing surface with module-level navigation.
            </template>
            <template v-else>
              Use Microsoft sign-in to restore your session, then return here as the default entry point into the recruiting experience.
            </template>
          </p>

          <div class="hero-metrics">
            <div class="hero-metric">
              <span>Session</span>
              <strong>{{ isAuthenticated ? 'Authenticated' : authLoading ? 'Checking' : 'Logged out' }}</strong>
            </div>
            <div class="hero-metric">
              <span>Role</span>
              <strong>{{ user?.role || 'Guest' }}</strong>
            </div>
            <div class="hero-metric">
              <span>Default View</span>
              <strong>Home Base</strong>
            </div>
          </div>

          <p v-if="authStatus" class="session-status">{{ authStatus }}</p>

          <div class="hero-rail" aria-label="Platform highlights">
            <div class="rail-item">
              <span class="rail-kicker">01</span>
              <div>
                <strong>Role-aware access</strong>
                <p>Authentication status stays visible without pulling focus from the product modules.</p>
              </div>
            </div>

            <div class="rail-item">
              <span class="rail-kicker">02</span>
              <div>
                <strong>Expandable modules</strong>
                <p>Cards are structured for live routes now and future workflow sections later.</p>
              </div>
            </div>
          </div>
        </section>

        <aside class="brief-panel">
          <p class="brief-label">At a glance</p>
          <div class="brief-grid">
            <div class="brief-card">
              <span>Active Surface</span>
              <strong>Dashboard shell</strong>
              <p>Warm glass treatment, stronger type scale, and consistent spacing across views.</p>
            </div>
            <div class="brief-card">
              <span>Featured Module</span>
              <strong>Evaluation cards</strong>
              <p>Recruiting card demo now sits inside a tighter, more cohesive application frame.</p>
            </div>
          </div>
        </aside>
      </div>

      <div class="menu-grid">
        <MenuCard
          v-for="card in homeMenuCards"
          :key="card.id"
          :card="card"
          @select="handleCardSelect"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.home-page {
  min-height: calc(100vh - 4rem);
  color: var(--text);
}

.page-shell {
  width: 100%;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.85fr);
  gap: 1.4rem;
  margin-bottom: 1.5rem;
}

.hero-panel,
.brief-panel {
  display: grid;
  gap: 1rem;
  align-content: start;
  padding: 1.5rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(255, 202, 125, 0.09), transparent 32%),
    var(--bg-panel);
  box-shadow: var(--shadow-lg);
}

.panel-label {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}

.hero-panel h2 {
  margin: 0;
  max-width: 13ch;
  font-size: clamp(2rem, 3.5vw, 3.3rem);
  line-height: 0.94;
  letter-spacing: -0.04em;
}

.panel-copy {
  margin: 0;
  max-width: 40rem;
  color: var(--text-muted);
  line-height: 1.7;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
}

.hero-metric,
.brief-card {
  padding: 1rem 1.05rem;
  border-radius: var(--radius-md);
  background: rgba(255, 246, 232, 0.04);
  border: 1px solid rgba(255, 239, 208, 0.08);
}

.hero-metric span,
.brief-label,
.brief-card span,
.rail-kicker {
  color: var(--text-subtle);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-metric strong,
.brief-card strong {
  display: block;
  margin-top: 0.42rem;
  font-size: 1.1rem;
  color: var(--text);
}

.session-status {
  margin: 0;
  color: var(--text-muted);
}

.hero-rail {
  display: grid;
  gap: 0.85rem;
  margin-top: 0.35rem;
}

.rail-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.9rem;
  align-items: start;
  padding-top: 0.95rem;
  border-top: 1px solid rgba(255, 239, 208, 0.08);
}

.rail-kicker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 800;
}

.rail-item strong {
  display: block;
  margin-bottom: 0.3rem;
}

.rail-item p,
.brief-card p {
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  line-height: 1.6;
}

.brief-panel {
  background:
    linear-gradient(180deg, rgba(255, 149, 90, 0.08), transparent 35%),
    rgba(31, 21, 18, 0.88);
}

.brief-grid {
  display: grid;
  gap: 0.9rem;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.4rem;
}

@media (max-width: 920px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }

  .hero-metrics {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .home-page {
    min-height: calc(100vh - 2.4rem);
  }

  .hero-panel,
  .brief-panel {
    padding: 1.15rem;
    border-radius: 24px;
  }
}
</style>
