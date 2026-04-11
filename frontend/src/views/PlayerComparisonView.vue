<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import ComparisonBar from '../components/ComparisonBar.vue'
import PlayerCard from '../components/PlayerCard.vue'
import { useRecruitingStore } from '../store/useRecruitingStore'

const router = useRouter()
const { state, comparePlayers, toggleComparePlayer } = useRecruitingStore()
const searchQuery = ref('')

const categories = [
  ['Physical', 'physical'],
  ['Athletic', 'athletic'],
  ['Production', 'production'],
  ['Context', 'context'],
]

const hasEnoughPlayers = computed(() => comparePlayers.value.length >= 2)
const normalizedSearch = computed(() => searchQuery.value.trim().toLowerCase())
const visibleSearchResults = computed(() => {
  const matches = state.players.filter((player) => {
    if (state.compareSelection.includes(player.id)) {
      return false
    }

    if (!normalizedSearch.value) {
      return true
    }

    return [player.name, player.position, player.school, player.city, player.state]
      .join(' ')
      .toLowerCase()
      .includes(normalizedSearch.value)
  })

  return matches.slice(0, 8)
})
const hiddenSearchCount = computed(() => {
  if (!normalizedSearch.value) {
    return Math.max(state.players.length - state.compareSelection.length - visibleSearchResults.value.length, 0)
  }

  const totalMatches = state.players.filter((player) => {
    if (state.compareSelection.includes(player.id)) {
      return false
    }

    return [player.name, player.position, player.school, player.city, player.state]
      .join(' ')
      .toLowerCase()
      .includes(normalizedSearch.value)
  }).length

  return Math.max(totalMatches - visibleSearchResults.value.length, 0)
})

function openPlayer(playerId) {
  router.push(`/players/${playerId}`)
}

function comparePlayer(playerId) {
  if (!state.compareSelection.includes(playerId) || state.compareSelection.length > 2) {
    toggleComparePlayer(playerId)
  }
}

function addPlayerToCompare(playerId) {
  toggleComparePlayer(playerId)
  searchQuery.value = ''
}
</script>

<template>
  <section class="compare-layout">
    <section class="compare-header surface-panel">
      <div>
        <p class="eyebrow section-label">Comparison Page</p>
        <h2>Build a side-by-side recruiting view.</h2>
        <p>Search for players to add them to the comparison board. The selection persists locally while you move around the prototype.</p>
      </div>

      <div class="compare-picker">
        <label class="search-field">
          <span class="sr-only">Search players to compare</span>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search by name, position, school, or location"
          >
        </label>

        <div class="selected-players" v-if="comparePlayers.length">
          <button
            v-for="player in comparePlayers"
            :key="player.id"
            class="selected-chip"
            type="button"
            @click="toggleComparePlayer(player.id)"
          >
            <span>{{ player.name }}</span>
            <small>{{ player.position }} • Remove</small>
          </button>
        </div>

        <div v-if="visibleSearchResults.length" class="search-results">
          <button
            v-for="player in visibleSearchResults"
            :key="player.id"
            class="search-result"
            type="button"
            @click="addPlayerToCompare(player.id)"
          >
            <strong>{{ player.name }}</strong>
            <span>{{ player.position }} • {{ player.school }}</span>
            <small>{{ player.city }}, {{ player.state }}</small>
          </button>
        </div>

        <p v-else class="search-empty">
          {{ normalizedSearch ? 'No players matched that search.' : 'Start typing to narrow the board and add more players.' }}
        </p>

        <p v-if="hiddenSearchCount > 0" class="search-meta">
          Showing the first {{ visibleSearchResults.length }} matches. Refine the search to narrow {{ hiddenSearchCount }} more.
        </p>
      </div>
    </section>

    <section v-if="hasEnoughPlayers" class="card-grid">
      <PlayerCard
        v-for="player in comparePlayers"
        :key="player.id"
        :player="player"
        compact
        @open="openPlayer"
        @compare="comparePlayer"
      />
    </section>

    <section v-if="hasEnoughPlayers" class="compare-panel surface-panel">
      <div class="section-head">
        <p class="eyebrow section-label">Category Breakdown</p>
        <h3>Mock side-by-side bars</h3>
      </div>

      <div v-for="[label, key] in categories" :key="key" class="category-block">
        <div class="category-heading">
          <strong>{{ label }}</strong>
        </div>

        <div class="category-bars">
          <ComparisonBar
            v-for="player in comparePlayers"
            :key="`${player.id}-${key}`"
            :label="label"
            :left-value="player.breakdown[key]"
            :right-value="100 - player.breakdown[key]"
            :left-label="player.name.split(' ')[0]"
            right-label="Remaining"
          />
        </div>
      </div>
    </section>

    <section v-if="hasEnoughPlayers" class="summary-grid">
      <article v-for="player in comparePlayers" :key="player.id" class="summary-card surface-panel">
        <span>{{ player.name }}</span>
        <strong>{{ player.comparisonScore }}</strong>
        <p>Scheme fit {{ player.schemeFit }} • Confidence {{ player.confidenceScore }}</p>
      </article>
    </section>

    <section v-else class="compare-panel empty-panel surface-panel empty-state">
      <p class="eyebrow section-label">Comparison Page</p>
      <h3>Select at least two players.</h3>
      <p>The compare view will populate as soon as you choose a second player.</p>
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
.empty-panel h3 {
  margin: 0.3rem 0 0;
}

.compare-header p:last-child,
.summary-card p,
.empty-panel p:last-child {
  margin: 0.35rem 0 0;
  color: var(--text-muted);
}

.card-grid,
.summary-grid,
.category-bars {
  display: grid;
  gap: 0.85rem;
}

.compare-picker,
.selected-players,
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

.selected-players {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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

.selected-chip span {
  color: var(--text);
}

.search-results {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.selected-chip small,
.search-result span,
.search-result small,
.search-empty,
.search-meta {
  color: var(--text-subtle);
}

.search-result strong {
  font-size: 0.98rem;
  color: var(--text);
}

.search-empty,
.search-meta {
  margin: 0;
}

.category-block {
  display: grid;
  gap: 0.9rem;
}

.category-heading strong {
  font-size: 1rem;
}

.summary-card span {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-subtle);
}

.summary-card strong {
  font-size: 1.6rem;
  color: var(--accent-strong);
}

@media (min-width: 900px) {
  .card-grid,
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
