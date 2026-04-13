<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import FilterPanel from '../components/FilterPanel.vue'
import PlayerCard from '../components/PlayerCard.vue'
import { useRecruitingStore } from '../store/useRecruitingStore'

const router = useRouter()
const { state, filteredPlayers, setFilters, toggleComparePlayer } = useRecruitingStore()

const filterOptions = computed(() => ({
  positions: ['All', ...new Set(state.players.map((player) => player.position))],
  states: ['All', ...new Set(state.players.map((player) => player.state))],
  statuses: ['All', ...new Set(state.players.map((player) => player.evaluationStatus))],
}))

function updateFilters(nextFilters) {
  setFilters(nextFilters)
}

function openPlayer(playerId) {
  router.push(`/players/${playerId}`)
}

function comparePlayer(playerId) {
  toggleComparePlayer(playerId)
  router.push('/compare')
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

    <FilterPanel
      class="sidebar"
      :filters="state.filters"
      :options="filterOptions"
      @update:filters="updateFilters"
    />

    <section class="results-panel surface-panel">
      <div class="results-header">
        <div>
          <p class="eyebrow section-label">Board Results</p>
          <h3>{{ filteredPlayers.length }} players matched</h3>
        </div>
      </div>

      <div v-if="filteredPlayers.length" class="player-grid">
        <PlayerCard
          v-for="player in filteredPlayers"
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

.intro-panel h2,
.results-header h3 {
  margin: 0.3rem 0 0;
}

.intro-panel p:last-child {
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
