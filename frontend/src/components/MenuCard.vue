<script setup>
import { computed } from 'vue'

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['select'])

const cardStyle = computed(() => ({
  '--card-accent-from': props.card?.accent?.from || '#f6c24d',
  '--card-accent-to': props.card?.accent?.to || '#f97316',
  '--card-shadow': props.card?.accent?.shadow || 'rgba(249, 115, 22, 0.28)',
}))

function handleSelect() {
  if (!props.card?.disabled) {
    emit('select', props.card.id)
  }
}
</script>

<template>
  <article class="menu-card" :class="{ 'is-disabled': card.disabled }" :style="cardStyle">
    <div class="card-accent" />

    <div class="menu-card-top">
      <div>
        <p class="menu-card-eyebrow">{{ card.eyebrow }}</p>
        <h2>{{ card.title }}</h2>
      </div>

      <span class="menu-card-icon">{{ card.icon }}</span>
    </div>

    <p class="menu-card-copy">{{ card.description }}</p>

    <div v-if="card.stats?.length" class="menu-card-stats">
      <div v-for="stat in card.stats" :key="`${card.id}-${stat.label}`" class="menu-stat">
        <span class="menu-stat-label">{{ stat.label }}</span>
        <strong>{{ stat.value }}</strong>
      </div>
    </div>

    <div class="menu-card-footer">
      <span class="menu-card-badge">{{ card.badge }}</span>
      <button class="menu-card-button" type="button" :disabled="card.disabled" @click="handleSelect">
        {{ card.actionLabel }}
      </button>
    </div>
  </article>
</template>

<style scoped>
.menu-card {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: 1.15rem;
  min-height: 21rem;
  padding: 1.45rem;
  border: 1px solid var(--line);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 245, 226, 0.05), rgba(255, 245, 226, 0.01)),
    rgba(28, 20, 16, 0.88);
  box-shadow: var(--shadow-md);
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease;
}

.menu-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 194, 118, 0.26);
  box-shadow: 0 24px 54px rgba(0, 0, 0, 0.28);
}

.card-accent {
  position: absolute;
  inset: -1rem -1rem auto auto;
  width: 10rem;
  height: 10rem;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--card-accent-from), var(--card-accent-to));
  filter: blur(18px);
  opacity: 0.22;
  pointer-events: none;
}

.menu-card-top,
.menu-card-footer,
.menu-card-stats {
  position: relative;
  z-index: 1;
}

.menu-card-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}

.menu-card-eyebrow {
  margin: 0 0 0.45rem;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-subtle);
}

h2 {
  margin: 0;
  max-width: 12ch;
  font-size: 1.72rem;
  line-height: 0.98;
  letter-spacing: -0.04em;
}

.menu-card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  border: 1px solid rgba(255, 244, 225, 0.08);
  background: rgba(255, 248, 237, 0.05);
  font-size: 0.88rem;
  font-weight: 800;
  color: var(--text-muted);
}

.menu-card-copy {
  position: relative;
  z-index: 1;
  margin: 0;
  color: var(--text-muted);
  line-height: 1.7;
}

.menu-card-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.menu-stat {
  padding: 0.85rem 0.95rem;
  border-radius: 1rem;
  background: rgba(255, 247, 235, 0.04);
  border: 1px solid rgba(255, 238, 211, 0.08);
}

.menu-stat-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.73rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-subtle);
}

.menu-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: auto;
}

.menu-card-badge {
  display: inline-flex;
  align-items: center;
  min-height: 2.1rem;
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  background: rgba(255, 247, 235, 0.05);
  color: var(--text-muted);
  font-size: 0.8rem;
}

.menu-card-button {
  padding: 0.8rem 1rem;
  border: none;
  border-radius: 0.95rem;
  background: linear-gradient(135deg, var(--card-accent-from), var(--card-accent-to));
  color: #1a130f;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 16px 28px var(--card-shadow);
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    opacity 160ms ease;
}

.menu-card-button:hover:enabled {
  transform: translateY(-2px);
  box-shadow: 0 20px 36px var(--card-shadow);
}

.menu-card-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  box-shadow: none;
}

.is-disabled {
  opacity: 0.72;
}

@media (max-width: 560px) {
  .menu-card {
    min-height: auto;
  }

  .menu-card-stats {
    grid-template-columns: 1fr;
  }

  .menu-card-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
