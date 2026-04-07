<script setup>
import ScoreBadge from './ScoreBadge.vue'

defineProps({
  player: {
    type: Object,
    required: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['open', 'compare'])

function initials(name) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
}
</script>

<template>
  <article class="player-card" :class="{ compact }">
    <div class="card-top">
      <div class="identity-chip">{{ initials(player.name) }}</div>
      <div class="card-headline">
        <span class="player-position">{{ player.position }}</span>
        <h3>{{ player.name }}</h3>
        <p>{{ player.school }} • {{ player.state }}</p>
      </div>
      <div class="rating-block">
        <span>Rating</span>
        <strong>{{ player.rating }}</strong>
      </div>
    </div>

    <div class="card-hero">
      <div class="hero-copy">
        <p class="hero-label">{{ player.projectedPosition }}</p>
        <p class="hero-summary">{{ player.summary }}</p>
      </div>
      <div class="card-frame">
        <span class="frame-stars">{{ '★'.repeat(player.stars) }}</span>
        <span class="frame-jersey">{{ player.jersey }}</span>
      </div>
    </div>

    <div class="measure-grid">
      <div>
        <span>Height</span>
        <strong>{{ player.height }}</strong>
      </div>
      <div>
        <span>Weight</span>
        <strong>{{ player.weight }} lbs</strong>
      </div>
      <div>
        <span>40 Time</span>
        <strong>{{ player.fortyTime }}</strong>
      </div>
      <div>
        <span>Status</span>
        <strong>{{ player.evaluationStatus }}</strong>
      </div>
    </div>

    <div class="score-row">
      <ScoreBadge label="Comp" :value="player.comparisonScore" tone="gold" />
      <ScoreBadge label="Fit" :value="player.schemeFit" tone="mint" />
      <ScoreBadge label="Trust" :value="player.confidenceScore" tone="blue" />
    </div>

    <div class="card-actions">
      <button class="primary-button" type="button" @click="emit('open', player.id)">
        Open Card
      </button>
      <button class="secondary-button" type="button" @click="emit('compare', player.id)">
        Compare
      </button>
    </div>
  </article>
</template>

<style scoped>
.player-card {
  display: grid;
  gap: 1rem;
  padding: 1.05rem;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    radial-gradient(circle at top right, rgba(255, 183, 94, 0.16), transparent 36%),
    linear-gradient(180deg, rgba(48, 33, 27, 0.98), rgba(27, 22, 27, 0.96));
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
}

.card-top,
.card-hero,
.card-actions {
  display: flex;
  gap: 0.9rem;
}

.card-top {
  align-items: start;
}

.identity-chip,
.card-frame {
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.identity-chip {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 18px;
  background: linear-gradient(135deg, #ffb75e, #ff7d54);
  color: #1c1511;
  font-size: 1rem;
  font-weight: 900;
}

.card-headline {
  flex: 1;
  min-width: 0;
}

.player-position,
.measure-grid span,
.rating-block span,
.hero-label {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(242, 236, 227, 0.52);
}

.card-headline h3 {
  margin: 0.3rem 0 0;
  font-size: 1.4rem;
  line-height: 1;
}

.card-headline p,
.hero-summary {
  margin: 0.35rem 0 0;
  color: rgba(242, 236, 227, 0.72);
}

.rating-block {
  display: grid;
  justify-items: end;
}

.rating-block strong {
  font-size: 2rem;
  color: #ffcd7a;
}

.card-hero {
  justify-content: space-between;
  align-items: stretch;
}

.hero-copy {
  flex: 1;
}

.card-frame {
  width: 5.8rem;
  min-height: 7rem;
  padding: 0.8rem;
  border-radius: 24px;
  border: 1px solid rgba(255, 224, 173, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 183, 94, 0.24), rgba(255, 255, 255, 0.04)),
    rgba(255, 255, 255, 0.03);
}

.frame-stars {
  color: #ffcd7a;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}

.frame-jersey {
  font-size: 1.8rem;
  font-weight: 900;
}

.measure-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.measure-grid div {
  display: grid;
  gap: 0.32rem;
  padding: 0.75rem 0.85rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
}

.measure-grid strong {
  font-size: 1rem;
}

.score-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.card-actions {
  flex-direction: column;
}

.secondary-button {
  min-height: 3rem;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  font-weight: 800;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.05);
  color: #f2ece3;
}

.compact {
  padding: 0.95rem;
}

@media (min-width: 720px) {
  .card-actions {
    flex-direction: row;
  }
}
</style>
