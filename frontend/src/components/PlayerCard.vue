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

function formatStatLabel(label) {
  return label
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .trim()
}

function getStatEntries(player) {
  return Object.entries(player?.stats || {})
}

function parseComparableStatValue(value) {
  if (typeof value === 'number') {
    return value
  }

  if (typeof value === 'string') {
    const normalized = Number.parseFloat(value.replace('%', '').trim())
    return Number.isFinite(normalized) ? normalized : null
  }

  return null
}

function getBestStatEntry(player) {
  let bestEntry = null

  for (const [key, value] of getStatEntries(player)) {
    const comparableValue = parseComparableStatValue(value)

    if (comparableValue === null) {
      continue
    }

    if (!bestEntry || comparableValue > bestEntry.rankValue) {
      bestEntry = {
        label: formatStatLabel(key),
        value,
        rankValue: comparableValue,
      }
    }
  }

  return bestEntry
}

function getSummaryEntries(player, compact) {
  if (!compact) {
    return getStatEntries(player).map(([key, value]) => ({
      key,
      label: formatStatLabel(key),
      value,
    }))
  }

  const bestStat = getBestStatEntry(player)
  const entries = [
    {
      key: 'height',
      label: 'Height',
      value: player?.height || 'N/A',
    },
    {
      key: 'weight',
      label: 'Weight',
      value: player?.weight ? `${player.weight} lbs` : 'N/A',
    },
    {
      key: bestStat?.label || 'best-stat',
      label: bestStat?.label || 'Best Stat',
      value: bestStat?.value ?? 'N/A',
    },
    {
      key: 'type',
      label: 'Type',
      value: player?.type || 'N/A',
    },
  ]

  return entries
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
      <div v-for="entry in getSummaryEntries(player, compact)" :key="entry.key">
        <span>{{ entry.label }}</span>
        <strong>{{ entry.value }}</strong>
      </div>
      <div v-if="!getSummaryEntries(player, compact).length" class="empty-stat">
        <span>Stats</span>
        <strong>No stats available</strong>
      </div>
    </div>

    <div class="score-row">
      <ScoreBadge label="Physical" :value="player.breakdown?.physical" tone="gold" />
      <ScoreBadge label="Production" :value="player.breakdown?.production" tone="mint" />
      <ScoreBadge label="Context" :value="player.breakdown?.context" tone="blue" />
    </div>

    <div class="card-actions">
      <button class="primary-button" type="button" @click="emit('open', player.id)">
        Open Card
      </button>
      <button v-if="!player.isHistorical" class="secondary-button" type="button" @click="emit('compare', player.id)">
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
  border: 1px solid var(--line);
  background:
    radial-gradient(circle at top right, rgba(217, 151, 0, 0.18), transparent 36%),
    linear-gradient(180deg, rgba(14, 38, 80, 0.98), rgba(8, 24, 53, 0.96));
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
  background: linear-gradient(135deg, var(--accent), var(--accent-strong));
  color: #102445;
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
  color: var(--text-subtle);
}

.card-headline h3 {
  margin: 0.3rem 0 0;
  font-size: 1.4rem;
  line-height: 1;
}

.card-headline p,
.hero-summary {
  margin: 0.35rem 0 0;
  color: var(--text-muted);
}

.rating-block {
  display: grid;
  justify-items: end;
}

.rating-block strong {
  font-size: 2rem;
  color: var(--accent-strong);
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
  border: 1px solid var(--line-strong);
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.24), rgba(255, 255, 255, 0.04)),
    rgba(255, 255, 255, 0.03);
}

.frame-stars {
  color: var(--accent-strong);
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
  background: var(--bg-soft);
}

.measure-grid strong {
  font-size: 1rem;
}

.empty-stat {
  grid-column: 1 / -1;
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
  background: var(--bg-soft);
  color: var(--text);
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
