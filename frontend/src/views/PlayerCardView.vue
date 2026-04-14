<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import PlayerCard from '../components/PlayerCard.vue'
import ScoreBadge from '../components/ScoreBadge.vue'
import { deletePlayerRecord } from '../services/recruitingClient'

const props = defineProps({
  playerId: {
    type: String,
    required: true,
  },
})

const router = useRouter()
const player = ref(null)
const comparables = ref([])
const previousPlayerId = ref(null)
const nextPlayerId = ref(null)
const loading = ref(true)
const deleting = ref(false)

async function loadPlayer() {
  loading.value = true
  player.value = null
  comparables.value = []
  previousPlayerId.value = null
  nextPlayerId.value = null

  try {
    const res = await fetch(`/api/recruits/${props.playerId}`, {
      credentials: 'include',
    })
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    const payload = await res.json()
    player.value = payload.player || null
    comparables.value = Array.isArray(payload.comparables) ? payload.comparables : []
    previousPlayerId.value = payload.previousPlayerId || null
    nextPlayerId.value = payload.nextPlayerId || null
  } catch {
    player.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.playerId,
  () => {
    loadPlayer()
  }
)

onMounted(() => {
  loadPlayer()
})

const playerSubtitle = computed(() => {
  if (!player.value) {
    return ''
  }

  if (player.value.isHistorical) {
    return `${player.value.projectedPosition} • ${player.value.school} • Last active ${player.value.classYear}`
  }

  return `${player.value.projectedPosition} • ${player.value.school} • Class of ${player.value.classYear}`
})

function openComparison(playerId) {
  router.push(`/compare?recruitId=${playerId}`)
}

function openPlayer(playerId) {
  router.push(`/players/${playerId}`)
}

async function deletePlayer() {
  if (!player.value || player.value.isHistorical || deleting.value) {
    return
  }

  const confirmed = window.confirm(`Delete ${player.value.name}?`)
  if (!confirmed) {
    return
  }

  deleting.value = true
  try {
    await deletePlayerRecord(player.value.id)
    router.push('/players')
  } catch (error) {
    console.error('Error deleting player:', error?.message || error)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <section v-if="loading" class="content-panel surface-panel">
    <p class="eyebrow section-label">Player Card</p>
    <h2>Loading player...</h2>
  </section>

  <section v-else-if="player" class="detail-layout">
    <div class="detail-main">
      <div class="page-header">
        <div>
          <p class="eyebrow section-label">Player Card</p>
          <h2>{{ player.name }}</h2>
          <p>{{ playerSubtitle }}</p>
        </div>
        <div class="header-actions">
          <button class="ghost-button" type="button" @click="router.push('/players')">Back to board</button>
          <button
            v-if="!player.isHistorical"
            class="delete-button"
            type="button"
            :disabled="deleting"
            @click="deletePlayer"
          >
            {{ deleting ? 'Deleting...' : 'Delete Player' }}
          </button>
        </div>
      </div>

      <PlayerCard :player="player" @compare="openComparison" @open="openPlayer" />

      <section class="content-panel surface-panel">
        <div class="section-header">
          <div>
            <p class="eyebrow section-label">Scoring</p>
            <h3>Evaluation summary</h3>
          </div>
        </div>

        <p class="body-copy">{{ player.explanation }}</p>

        <div class="score-row">
          <ScoreBadge label="Physical" :value="player.breakdown.physical" tone="gold" />
          <ScoreBadge label="Production" :value="player.breakdown.production" tone="mint" />
          <ScoreBadge label="Context" :value="player.breakdown.context" tone="blue" />
        </div>
      </section>

      <section v-if="!player.isHistorical" class="content-panel surface-panel">
        <div class="section-header">
          <div>
            <p class="eyebrow section-label">Player Navigation</p>
            <h3>Move through the board</h3>
          </div>
        </div>

        <div class="nav-row">
          <button class="ghost-button" type="button" :disabled="!previousPlayerId" @click="openPlayer(previousPlayerId)">
            Previous Player
          </button>
          <button class="ghost-button" type="button" :disabled="!nextPlayerId" @click="openPlayer(nextPlayerId)">
            Next Player
          </button>
        </div>
      </section>
    </div>

    <aside class="detail-side">
      <section class="content-panel surface-panel">
        <p class="eyebrow section-label">Vitals + Production</p>
        <div class="detail-grid">
          <div><span>Height</span><strong>{{ player.height }}</strong></div>
          <div><span>Weight</span><strong>{{ player.weight ? `${player.weight} lbs` : 'N/A' }}</strong></div>
          <div><span>40 Time</span><strong>{{ player.fortyTime || 'N/A' }}</strong></div>
          <div><span>GPA</span><strong>{{ player.gpa ?? 'N/A' }}</strong></div>
          <div v-for="(value, key) in player.stats" :key="key">
            <span>{{ key.replace(/([A-Z])/g, ' $1') }}</span>
            <strong>{{ value }}</strong>
          </div>
        </div>
      </section>

      <section class="content-panel surface-panel">
        <p class="eyebrow section-label">Coach Notes</p>
        <p class="body-copy">{{ player.notes }}</p>
      </section>

      <section v-if="comparables.length" class="content-panel surface-panel">
        <div class="section-header">
          <div>
            <p class="eyebrow section-label">Top Comparables</p>
            <h3>Nearest matches</h3>
          </div>
        </div>

        <div class="compare-list">
          <button
            v-for="comparable in comparables"
            :key="comparable.id"
            class="compare-row"
            type="button"
            @click="openComparison(comparable.id)"
          >
            <div>
              <strong>{{ comparable.name }}</strong>
              <p>{{ comparable.projectedPosition }}</p>
            </div>
          </button>
        </div>
      </section>
    </aside>
  </section>

  <section v-else class="content-panel surface-panel">
    <p class="eyebrow section-label">Player Card</p>
    <h2>Player not found</h2>
  </section>
</template>

<style scoped>
.detail-layout {
  display: grid;
  gap: 1rem;
}

.detail-main,
.detail-side {
  display: grid;
  gap: 1rem;
}

.page-header,
.section-header,
.compare-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.page-header {
  align-items: start;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.page-header h2,
.section-header h3 {
  margin: 0.3rem 0 0;
}

.page-header p,
.body-copy,
.compare-row p {
  margin: 0.35rem 0 0;
  color: rgba(242, 236, 227, 0.72);
}

.nav-row {
  display: grid;
  gap: 0.75rem;
}

.score-row,
.detail-grid {
  display: grid;
  gap: 0.8rem;
}

.compare-list {
  display: grid;
  gap: 0.9rem;
}

.detail-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-grid div {
  display: grid;
  gap: 0.35rem;
  padding: 0.85rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
}

.detail-grid span {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(242, 236, 227, 0.52);
}

.compare-row,
.ghost-button {
  cursor: pointer;
}

.delete-button {
  cursor: pointer;
  padding: 0.75rem 1rem;
  border-radius: 14px;
  border: 1px solid rgba(248, 113, 113, 0.45);
  background: rgba(127, 29, 29, 0.16);
  color: #fca5a5;
  font-weight: 700;
}

.delete-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.compare-row {
  align-items: center;
  padding: 0.95rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  text-align: left;
}

@media (min-width: 980px) {
  .detail-layout {
    grid-template-columns: minmax(0, 1.25fr) 360px;
    align-items: start;
  }

  .detail-side {
    position: sticky;
    top: 1rem;
  }

  .score-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .nav-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
