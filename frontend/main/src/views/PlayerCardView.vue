<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import PlayerCard from '../components/PlayerCard.vue'
import ComparisonBar from '../components/ComparisonBar.vue'
import ScoreBadge from '../components/ScoreBadge.vue'
import { getComparables, getPlayerById } from '../data/mockRecruitingData'
import { useRecruitingStore } from '../store/useRecruitingStore'

const props = defineProps({
  playerId: {
    type: String,
    required: true,
  },
})

const router = useRouter()
const { state, toggleComparePlayer } = useRecruitingStore()

const player = computed(() => getPlayerById(props.playerId))
const comparables = computed(() => (player.value ? getComparables(player.value) : []))
const playerIndex = computed(() => state.players.findIndex((entry) => entry.id === props.playerId))
const previousPlayerId = computed(() =>
  playerIndex.value > 0 ? state.players[playerIndex.value - 1].id : null
)
const nextPlayerId = computed(() =>
  playerIndex.value >= 0 && playerIndex.value < state.players.length - 1
    ? state.players[playerIndex.value + 1].id
    : null
)

function openComparison(comparableId) {
  toggleComparePlayer(props.playerId)
  toggleComparePlayer(comparableId)
  router.push('/compare')
}

function openPlayer(playerId) {
  router.push(`/players/${playerId}`)
}
</script>

<template>
  <section v-if="player" class="detail-layout">
    <div class="detail-main">
      <div class="page-header">
        <div>
          <p class="eyebrow section-label">Player Card</p>
          <h2>{{ player.name }}</h2>
          <p>{{ player.projectedPosition }} • {{ player.school }} • Class of {{ player.classYear }}</p>
        </div>
        <button class="ghost-button" type="button" @click="router.push('/players')">Back to board</button>
      </div>

      <PlayerCard :player="player" @compare="openComparison" @open="openPlayer" />

      <section class="content-panel surface-panel">
        <div class="section-header">
          <div>
            <p class="eyebrow section-label">Scoring</p>
            <h3>Evaluation summary</h3>
          </div>
        </div>

        <div class="score-row">
          <ScoreBadge label="Comparison" :value="player.comparisonScore" tone="gold" />
          <ScoreBadge label="Scheme Fit" :value="player.schemeFit" tone="mint" />
          <ScoreBadge label="Confidence" :value="player.confidenceScore" tone="blue" />
        </div>

        <p class="body-copy">{{ player.explanation }}</p>

        <div class="bars">
          <ComparisonBar
            label="Physical"
            :left-value="player.breakdown.physical"
            :right-value="100 - player.breakdown.physical"
            left-label="Score"
            right-label="Headroom"
          />
          <ComparisonBar
            label="Athletic"
            :left-value="player.breakdown.athletic"
            :right-value="100 - player.breakdown.athletic"
            left-label="Score"
            right-label="Headroom"
          />
          <ComparisonBar
            label="Production"
            :left-value="player.breakdown.production"
            :right-value="100 - player.breakdown.production"
            left-label="Score"
            right-label="Headroom"
          />
          <ComparisonBar
            label="Context"
            :left-value="player.breakdown.context"
            :right-value="100 - player.breakdown.context"
            left-label="Score"
            right-label="Headroom"
          />
        </div>
      </section>

      <section class="content-panel surface-panel">
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
          <div><span>Weight</span><strong>{{ player.weight }} lbs</strong></div>
          <div><span>40 Time</span><strong>{{ player.fortyTime }}</strong></div>
          <div><span>GPA</span><strong>{{ player.gpa }}</strong></div>
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

      <section class="content-panel surface-panel">
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
            <span>{{ comparable.comparisonScore }}</span>
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

.bars,
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

.compare-row {
  align-items: center;
  padding: 0.95rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  text-align: left;
}

.compare-row span {
  font-size: 1.3rem;
  font-weight: 900;
  color: #79c8ff;
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
