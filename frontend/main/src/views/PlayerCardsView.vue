<script setup>
import { onMounted, ref } from 'vue'

import AppShellHeader from '../components/AppShellHeader.vue'
import PlayerCard from '../components/PlayerCard.vue'
import testPlayers from '../data/testplayers.json'

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

const emit = defineEmits(['navigate'])

const players = ref([])
const loading = ref(true)

onMounted(() => {
  players.value = Array.isArray(testPlayers) ? testPlayers : []
  loading.value = false
})
</script>

<template>
  <section class="player-cards-page">
    <div class="page-shell">
      <AppShellHeader
        eyebrow="Evaluation Surface"
        title="Recruiting cards with a stronger presentation layer."
        description="The card board now sits inside the same warmer shell as the landing page, so the demo reads like part of a product instead of a separate prototype."
      />

      <section class="board-summary">
        <div class="summary-card">
          <span>Board Mode</span>
          <strong>{{ loading ? 'Loading roster' : `${players.length} cards ready` }}</strong>
          <p>Tap a card to flip it and inspect scoring, context, and AI explanation details.</p>
        </div>
        <div class="summary-card">
          <span>Scoring Signals</span>
          <strong>Comparison, fit, confidence</strong>
          <p>The layout emphasizes fast top-line review without hiding the reasoning behind each score.</p>
        </div>
      </section>

      <p v-if="loading" class="state-message">Loading players...</p>
      <p v-else-if="!players.length" class="state-message">No players found.</p>

      <div v-else class="card-grid">
        <PlayerCard
          v-for="player in players"
          :key="player.id"
          :player="player"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.player-cards-page {
  min-height: calc(100vh - 4rem);
  color: var(--text);
}

.page-shell {
  width: 100%;
}

.board-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1.4rem;
}

.summary-card {
  padding: 1.15rem 1.2rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(255, 193, 114, 0.08), transparent 36%),
    rgba(27, 20, 17, 0.86);
  box-shadow: var(--shadow-md);
}

.summary-card span {
  color: var(--text-subtle);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.summary-card strong {
  display: block;
  margin-top: 0.5rem;
  font-size: 1.2rem;
  letter-spacing: -0.03em;
}

.summary-card p {
  margin: 0.45rem 0 0;
  color: var(--text-muted);
  line-height: 1.6;
}

.state-message {
  padding: 1.5rem 0;
  color: var(--text-muted);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.6rem;
}

@media (max-width: 640px) {
  .player-cards-page {
    min-height: calc(100vh - 2.4rem);
  }

  .board-summary {
    grid-template-columns: 1fr;
  }
}
</style>
