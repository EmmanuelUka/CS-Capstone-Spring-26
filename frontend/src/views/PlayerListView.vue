<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import FilterPanel from '../components/FilterPanel.vue'
import PlayerCard from '../components/PlayerCard.vue'
import { useRecruitingStore } from '../store/useRecruitingStore'

const router = useRouter()
const { state, setFilters } = useRecruitingStore()

const players = ref([])
const filterOptions = ref({
  positions: ['All'],
  states: ['All'],
  types: ['All'],
})
const loading = ref(true)
const error = ref('')

async function loadPlayers() {
  loading.value = true
  error.value = ''

  try {
    const params = new URLSearchParams()
    if (state.filters.query) params.set('query', state.filters.query)
    if (state.filters.position !== 'All') params.set('position', state.filters.position)
    if (state.filters.state !== 'All') params.set('state', state.filters.state)
    if (state.filters.type !== 'All') params.set('type', state.filters.type)
    if (state.filters.ratingFloor > 0) params.set('ratingFloor', String(state.filters.ratingFloor))

    const queryString = params.toString()
    const res = await fetch(`/api/recruits${queryString ? `?${queryString}` : ''}`, {
      credentials: 'include',
    })
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    const payload = await res.json()
    players.value = Array.isArray(payload.players) ? payload.players : []
    filterOptions.value = {
      positions: ['All', ...(payload.positions || [])],
      states: ['All', ...(payload.states || [])],
      types: ['All', ...(payload.types || [])],
    }
  } catch (err) {
    players.value = []
    error.value = err.message || 'Unable to load players'
  } finally {
    loading.value = false
  }
}

watch(
  () => ({ ...state.filters }),
  () => {
    loadPlayers()
  },
  { deep: true }
)

onMounted(() => {
  loadPlayers()
})

function updateFilters(nextFilters) {
  setFilters(nextFilters)
}

function openPlayer(playerId) {
  router.push(`/players/${playerId}`)
}

function comparePlayer(playerId) {
  router.push(`/compare?recruitId=${playerId}`)
}
</script>

<template>
  <section class="list-layout">
    <div class="intro-panel surface-panel">
      <p class="eyebrow section-label">Player List</p>
      <h2>Search the full recruiting board quickly.</h2>
      <p>
        Mobile-friendly filters and a compact board layout make it easier for coaches to narrow the list without leaving the page.
      </p>
    </div>

    <aside class="sidebar sidebar-stack">
      <FilterPanel
        :filters="state.filters"
        :options="filterOptions"
        @update:filters="updateFilters"
      />

      <section class="add-player-panel surface-panel">
        <p class="eyebrow section-label">Board Tools</p>
        <h3>Add a new player</h3>
        <p>Open the intake page to enter a new prospect profile.</p>
        <button class="primary-button" type="button" @click="router.push('/players/add')">Add player</button>
      </section>
    </aside>

    <section class="results-panel surface-panel">
      <div class="results-header">
        <div>
          <p class="eyebrow section-label">Board Results</p>
          <h3>{{ loading ? 'Loading players...' : `${players.length} players matched` }}</h3>
        </div>
      </div>

      <div v-if="error" class="empty-state">
        <strong>Failed to load players.</strong>
        <p>{{ error }}</p>
      </div>

      <div v-else-if="loading" class="empty-state">
        <strong>Loading players.</strong>
        <p>Fetching the current board from the backend.</p>
      </div>

      <div v-else-if="players.length" class="player-grid">
        <PlayerCard
          v-for="player in players"
          :key="player.id"
          :player="player"
          compact
          @open="openPlayer"
          @compare="comparePlayer"
        />
      </div>

      <div v-else class="empty-state">
        <strong>No players match the current filters.</strong>
        <p>Adjust the search text or widen the filters to repopulate the board.</p>
      </div>
    </section>
  </section>
</template>

<style scoped>
.list-layout {
  display: grid;
  gap: 1rem;
}

.sidebar-stack {
  display: grid;
  gap: 1rem;
  align-self: start;
}

.intro-panel h2,
.results-header h3,
.add-player-panel h3 {
  margin: 0.3rem 0 0;
}

.intro-panel p:last-child,
.add-player-panel > p:last-child {
  margin: 0;
  color: rgba(242, 236, 227, 0.72);
}

.player-grid {
  display: grid;
  gap: 0.9rem;
}

.empty-state p {
  margin: 0.35rem 0 0;
  color: rgba(242, 236, 227, 0.72);
}

@media (min-width: 980px) {
  .list-layout {
    grid-template-columns: 320px minmax(0, 1fr);
    align-items: start;
  }

  .intro-panel {
    grid-column: 1 / -1;
  }

  .sidebar {
    position: sticky;
    top: 1rem;
  }

  .player-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
