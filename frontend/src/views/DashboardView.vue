<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { activityFeed } from '../data/mockRecruitingData'
import { useRecruitingStore } from '../store/useRecruitingStore'

const router = useRouter()
const { state } = useRecruitingStore()

// --- Dashboard stats from API ---
const dashboardStats = ref(null)
const statsLoading = ref(true)
const statsError = ref(null)

onMounted(async () => {
  try {
    const res = await fetch('api/dashboard_info')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    dashboardStats.value = await res.json()
  } catch (err) {
    statsError.value = err.message
  } finally {
    statsLoading.value = false
  }
})

// --- Remaining computed values (still from store) ---
const featuredPlayers = computed(() => state.players.slice(0, 3))
const shortlistSummaries = computed(() =>
  state.shortlists.map((list) => ({
    ...list,
    filledCount: list.slots.filter((slot) => slot.playerId).length,
    totalCount: list.slots.length,
  }))
)
</script>

<template>
  <section class="page-grid">
    <section class="hero-panel surface-panel">
      <p class="page-kicker section-label">Dashboard</p>
      <h2>Stay on top of the recruiting board from one screen.</h2>
      <p class="page-copy">
        Snapshot the active board, recent work, and the players most likely to move into the next decision window.
      </p>

      <div class="stats-grid">
        <article class="stat-card">
          <span>Total Players</span>
          <strong>{{ statsLoading ? '—' : dashboardStats?.total_players ?? '—' }}</strong>
          <p>Current mock board under review.</p>
        </article>
        <article class="stat-card">
          <span>Transfers</span>
          <strong>{{ statsLoading ? '—' : dashboardStats?.transfers ?? '—' }}</strong>
          <p>Portal prospects currently on the board.</p>
        </article>
        <article class="stat-card">
          <span>High School</span>
          <strong>{{ statsLoading ? '—' : dashboardStats?.high_school ?? '—' }}</strong>
          <p>Prep prospects currently tracked in the cycle.</p>
        </article>
        <article class="stat-card">
          <span>Avg Rating</span>
          <strong>{{ statsLoading ? '—' : dashboardStats?.avg_rating ?? '—' }}</strong>
          <p>Board quality benchmark across the dataset.</p>
        </article>
      </div>

      <p v-if="statsError" class="stats-error">Failed to load stats: {{ statsError }}</p>
    </section>

    <!-- rest of template unchanged -->
    <section class="stack-panel surface-panel">
      <div class="panel-header">
        <div>
          <p class="page-kicker section-label">Recent Recruits</p>
          <h3>Immediate attention</h3>
        </div>
        <button class="text-link" type="button" @click="router.push('/players')">Open board</button>
      </div>

      <div class="recruit-list">
        <button
          v-for="player in featuredPlayers"
          :key="player.id"
          class="recruit-row"
          type="button"
          @click="router.push(`/players/${player.id}`)"
        >
          <div>
            <strong>{{ player.name }}</strong>
            <p>{{ player.position }} • {{ player.school }}</p>
          </div>
          <span>{{ player.rating }}</span>
        </button>
      </div>
    </section>

    <section class="stack-panel surface-panel">
      <div class="panel-header">
        <div>
          <p class="page-kicker section-label">Activity</p>
          <h3>Recent movement</h3>
        </div>
      </div>

      <div class="activity-list">
        <article v-for="item in activityFeed" :key="item.id" class="activity-row">
          <div class="activity-dot" />
          <div>
            <strong>{{ item.label }}</strong>
            <p>{{ item.detail }}</p>
          </div>
          <span>{{ item.time }}</span>
        </article>
      </div>
    </section>

    <section class="stack-panel surface-panel">
      <div class="panel-header">
        <div>
          <p class="page-kicker section-label">Shortlists</p>
          <h3>Board groups</h3>
        </div>
        <button class="text-link" type="button" @click="router.push('/shortlists')">Manage</button>
      </div>

      <div class="shortlist-grid">
        <article v-for="list in shortlistSummaries" :key="list.id" class="shortlist-card">
          <span class="swatch" :style="{ background: list.color }" />
          <strong>{{ list.name }}</strong>
          <p>{{ list.filledCount }} of {{ list.totalCount }} positions filled</p>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.page-grid {
  display: grid;
  gap: 1rem;
}

.hero-panel h2,
.panel-header h3 {
  margin: 0.3rem 0 0;
}

.page-copy {
  margin: 0;
  max-width: 42rem;
  color: var(--text-muted);
}

.stats-grid,
.shortlist-grid {
  display: grid;
  gap: 0.8rem;
}

.stat-card,
.shortlist-card {
  padding: 0.95rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--line);
}

.stat-card span,
.shortlist-card p {
  color: var(--text-muted);
}

.stat-card strong {
  display: block;
  margin-top: 0.35rem;
  font-size: 1.6rem;
}

.stat-card p,
.recruit-row p,
.activity-row p,
.shortlist-card p {
  margin: 0.35rem 0 0;
}

.panel-header,
.recruit-row,
.activity-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.text-link,
.recruit-row {
  cursor: pointer;
}

.text-link {
  padding: 0;
  background: transparent;
  color: var(--accent);
  font-weight: 800;
}

.recruit-list,
.activity-list {
  display: grid;
  gap: 0.8rem;
}

.recruit-row {
  align-items: center;
  padding: 0.95rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--line);
  color: inherit;
  text-align: left;
}

.recruit-row span {
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--accent-strong);
}

.activity-row {
  align-items: start;
  padding: 0.95rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.activity-dot {
  width: 0.7rem;
  height: 0.7rem;
  margin-top: 0.3rem;
  border-radius: 999px;
  background: var(--brand-cool);
}

.activity-row > div:nth-child(2) {
  flex: 1;
}

.activity-row span:last-child {
  color: var(--text-subtle);
  font-size: 0.8rem;
}

.shortlist-card {
  display: grid;
  gap: 0.4rem;
}

.swatch {
  width: 2rem;
  height: 0.45rem;
  border-radius: 999px;
}

.stats-error {
  margin-top: 0.5rem;
  color: var(--error, #f87171);
  font-size: 0.85rem;
}

@media (min-width: 880px) {
  .page-grid {
    grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
  }

  .hero-panel {
    grid-column: 1 / -1;
  }

  .stats-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>