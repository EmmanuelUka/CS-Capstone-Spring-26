<template>
  <section class="player-cards-page">
    <div class="page-shell">
      <header class="page-header">
        <p class="eyebrow">Hashmark Recruiting Assistant</p>
        <h1>Evaluation Card Demo</h1>
        <p class="page-copy">
          FIFA-style recruiting cards using the system's real evaluation concepts:
          historical comparison, scheme fit, confidence, and transparent explanation.
        </p>
      </header>

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

<script setup>
import { onMounted, ref } from 'vue'

import PlayerCard from '../components/PlayerCard.vue'
import testPlayers from '../data/testplayers.json'

const players = ref([])
const loading = ref(true)

onMounted(() => {
  players.value = Array.isArray(testPlayers) ? testPlayers : []
  loading.value = false
})
</script>

<style scoped>
.player-cards-page {
  min-height: 100vh;
  padding: 2rem;
  background:
    radial-gradient(circle at top, rgba(245, 194, 66, 0.18), transparent 24%),
    linear-gradient(180deg, #09111f 0%, #101827 50%, #1b2434 100%);
  color: #f8fafc;
}

.page-shell {
  width: min(1240px, 100%);
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.eyebrow {
  margin: 0 0 0.45rem;
  font-size: 0.84rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #fbbf24;
}

.page-header h1 {
  margin: 0;
  font-size: clamp(2.2rem, 4vw, 3.6rem);
  line-height: 0.98;
  letter-spacing: -0.04em;
}

.page-copy {
  max-width: 48rem;
  margin: 0.85rem 0 0;
  line-height: 1.65;
  color: rgba(226, 232, 240, 0.82);
}

.state-message {
  padding: 2rem 0;
  color: rgba(226, 232, 240, 0.88);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.6rem;
}

@media (max-width: 640px) {
  .player-cards-page {
    padding: 1.2rem;
  }
}
</style>
