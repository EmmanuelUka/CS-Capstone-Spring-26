<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: Number,
    required: true,
  },
  tone: {
    type: String,
    default: 'gold',
  },
})

const badgeClass = computed(() => `tone-${props.tone}`)
const tier = computed(() => {
  if (props.value >= 90) {
    return 'Elite'
  }
  if (props.value >= 80) {
    return 'Strong'
  }
  return 'Developing'
})
</script>

<template>
  <div class="score-badge" :class="badgeClass">
    <span class="score-label">{{ label }}</span>
    <strong class="score-value">{{ value }}</strong>
    <span class="score-tier">{{ tier }}</span>
  </div>
</template>

<style scoped>
.score-badge {
  display: grid;
  gap: 0.2rem;
  min-width: 5.2rem;
  padding: 0.8rem 0.9rem;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
}

.score-label {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(242, 236, 227, 0.68);
}

.score-value {
  font-size: 1.3rem;
  line-height: 1;
  letter-spacing: -0.04em;
}

.score-tier {
  font-size: 0.72rem;
  color: rgba(242, 236, 227, 0.6);
}

.tone-gold .score-value {
  color: #ffcd7a;
}

.tone-mint .score-value {
  color: #93dfb2;
}

.tone-blue .score-value {
  color: #87c9ff;
}
</style>
