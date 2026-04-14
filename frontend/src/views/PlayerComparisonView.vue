<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ComparisonBar from '../components/ComparisonBar.vue'
import PlayerCard from '../components/PlayerCard.vue'

const router = useRouter()
const route = useRoute()
const searchQuery = ref('')
const activeRecruit = ref(null)
const historicalMatches = ref([])
const searchResults = ref([])

const normalizedSearch = computed(() => searchQuery.value.trim().toLowerCase())
const hiddenSearchCount = computed(() => 0)

async function loadActiveRecruit() {
  if (!route.query.recruitId) {
    activeRecruit.value = null
    historicalMatches.value = []
    return
  }

  try {
    const [playerRes, historicalRes] = await Promise.all([
      fetch(`/api/recruits/${route.query.recruitId}`, { credentials: 'include' }),
      fetch(`/api/recruits/${route.query.recruitId}/historical_matches`, { credentials: 'include' }),
    ])

    activeRecruit.value = playerRes.ok ? (await playerRes.json()).player || null : null
    historicalMatches.value = historicalRes.ok ? await historicalRes.json() : []
  } catch {
    activeRecruit.value = null
    historicalMatches.value = []
  }
}

async function loadSearchResults() {
  try {
    const params = new URLSearchParams({ limit: '8' })
    if (searchQuery.value.trim()) {
      params.set('query', searchQuery.value.trim())
    }
    if (activeRecruit.value?.id) {
      params.set('excludeId', String(activeRecruit.value.id))
    }

    const res = await fetch(`/api/recruits?${params.toString()}`, {
      credentials: 'include',
    })

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    const payload = await res.json()
    searchResults.value = Array.isArray(payload.players) ? payload.players : []
  } catch {
    searchResults.value = []
  }
}

watch(
  () => route.query.recruitId,
  async () => {
    await loadActiveRecruit()
    await loadSearchResults()
  },
  { immediate: true }
)

watch(
  () => searchQuery.value,
  () => {
    loadSearchResults()
  }
)

function openPlayer(playerId) {
  router.push(`/players/${playerId}`)
}

function openHistoricalPlayer(playerId) {
  router.push(`/players/${playerId}`)
}

function selectRecruit(playerId) {
  router.push(`/compare?recruitId=${playerId}`)
  searchQuery.value = ''
}

function clearRecruitSelection() {
  router.push('/compare')
}
</script>

<template>
  <section class="compare-layout">
    <section class="compare-header surface-panel">
      <div>
        <p class="eyebrow section-label">Comparison Page</p>
        <h2>Open a recruit and inspect their closest historical matches.</h2>
        <p>
          Select one recruit to see the ranked historical player list. SuperScore is the average of the historical
          comparison scores shown on the bars below.
        </p>
      </div>

      <div class="compare-picker">
        <label class="search-field">
          <span class="sr-only">Search recruits to compare</span>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search recruits by name, position, school, or location"
          >
        </label>

        <button v-if="activeRecruit" class="selected-chip" type="button" @click="clearRecruitSelection">
          <span>{{ activeRecruit.name }}</span>
          <small>{{ activeRecruit.position }} • Clear selection</small>
        </button>

        <div v-if="searchResults.length" class="search-results">
          <button
            v-for="player in searchResults"
            :key="player.id"
            class="search-result"
            type="button"
            @click="selectRecruit(player.id)"
          >
            <strong>{{ player.name }}</strong>
            <span>{{ player.position }} • {{ player.school }}</span>
            <small>{{ player.city }}, {{ player.state }}</small>
          </button>
        </div>

        <p v-else class="search-empty">
          {{ normalizedSearch ? 'No recruits matched that search.' : 'Select a recruit to load their historical matches.' }}
        </p>

        <p v-if="hiddenSearchCount > 0" class="search-meta">
          Showing the first {{ searchResults.length }} matches. Refine the search to narrow {{ hiddenSearchCount }} more.
        </p>
      </div>
    </section>

    <section v-if="activeRecruit" class="card-grid">
      <PlayerCard
        :player="activeRecruit"
        compact
        @open="openPlayer"
        @compare="selectRecruit"
      />
    </section>

    <section v-if="activeRecruit && historicalMatches.length" class="compare-panel surface-panel">
      <div class="section-head">
        <p class="eyebrow section-label">Historical Matches</p>
        <h3>{{ activeRecruit.name }} ranked by SuperScore</h3>
      </div>

      <div class="historical-grid">
        <button
          v-for="(match, index) in historicalMatches"
          :key="match.historicalId"
          class="historical-card"
          type="button"
          @click="openHistoricalPlayer(match.historicalId)"
        >
          <div class="historical-head">
            <div>
              <span class="match-rank">#{{ index + 1 }} Historical Match</span>
              <h4>{{ match.name }}</h4>
              <p>{{ match.position }} • {{ match.school }} • {{ match.conference }} • {{ match.lastSeason }}</p>
            </div>

            <div class="super-score">
              <span>SuperScore</span>
              <strong>{{ match.superScore }}</strong>
            </div>
          </div>

          <div class="historical-bars">
            <ComparisonBar
              :left-value="match.comparisonScores.physical"
              :right-value="100 - match.comparisonScores.physical"
              left-label="Physical"
              :value-display="match.comparisonScores.physical"
              right-label=""
            />
            <ComparisonBar
              :left-value="match.comparisonScores.production"
              :right-value="100 - match.comparisonScores.production"
              left-label="Production"
              :value-display="match.comparisonScores.production"
              right-label=""
            />
            <ComparisonBar
              :left-value="match.comparisonScores.context"
              :right-value="100 - match.comparisonScores.context"
              left-label="Context"
              :value-display="match.comparisonScores.context"
              right-label=""
            />
          </div>
        </button>
      </div>
    </section>

    <section v-else-if="activeRecruit" class="compare-panel surface-panel empty-state">
      <p class="eyebrow section-label">Historical Matches</p>
      <h3>No historical matches configured.</h3>
      <p>Add historical comparison results for this recruit to populate the page.</p>
    </section>

    <section v-else class="compare-panel empty-panel surface-panel empty-state">
      <p class="eyebrow section-label">Comparison Page</p>
      <h3>Select a recruit.</h3>
      <p>Once a recruit is selected, their closest historical players will appear here.</p>
    </section>
  </section>
</template>

<style scoped>
.compare-layout {
  display: grid;
  gap: 1rem;
}

.compare-header h2,
.section-head h3,
.historical-head h4,
.empty-panel h3 {
  margin: 0.3rem 0 0;
}

.compare-header p:last-child,
.historical-head p,
.empty-panel p:last-child {
  margin: 0.35rem 0 0;
  color: var(--text-muted);
}

.card-grid,
.historical-grid,
.historical-bars {
  display: grid;
  gap: 0.85rem;
}

.compare-picker,
.search-results {
  display: grid;
  gap: 0.85rem;
}

.search-field input {
  width: 100%;
  padding: 0.9rem 1rem;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--bg-soft);
  color: var(--text);
}

.selected-chip,
.search-result {
  display: grid;
  gap: 0.25rem;
  padding: 0.95rem;
  border: 0;
  text-align: left;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.045);
  cursor: pointer;
}

.selected-chip {
  outline: 1px solid rgba(217, 151, 0, 0.28);
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.12), rgba(217, 151, 0, 0.04)),
    rgba(255, 255, 255, 0.035);
}

.search-results {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.selected-chip span,
.search-result strong {
  color: var(--text);
}

.selected-chip small,
.search-result span,
.search-result small,
.search-empty,
.search-meta,
.match-rank,
.super-score span {
  color: var(--text-subtle);
}

.search-result strong {
  font-size: 0.98rem;
}

.search-empty,
.search-meta {
  margin: 0;
}

.historical-card {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border-radius: 22px;
  border: 1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.08), transparent 35%),
    rgba(255, 255, 255, 0.04);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.historical-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}

.match-rank,
.super-score span {
  display: block;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.super-score {
  display: grid;
  justify-items: end;
}

.super-score strong {
  font-size: 2rem;
  line-height: 1;
  color: var(--accent-strong);
}

@media (min-width: 900px) {
  .historical-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
