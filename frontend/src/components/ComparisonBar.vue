<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: '',
  },
  leftValue: {
    type: Number,
    required: true,
  },
  rightValue: {
    type: Number,
    required: true,
  },
  leftLabel: {
    type: String,
    default: 'Left',
  },
  rightLabel: {
    type: String,
    default: 'Right',
  },
})

const total = computed(() => Math.max(props.leftValue + props.rightValue, 1))
const leftWidth = computed(() => `${(props.leftValue / total.value) * 100}%`)
const rightWidth = computed(() => `${(props.rightValue / total.value) * 100}%`)
</script>

<template>
  <div class="comparison-bar">
    <div v-if="label" class="comparison-title">{{ label }}</div>

    <div class="comparison-row">
      <span class="comparison-side comparison-side-left">{{ leftLabel }} <strong>{{ leftValue }}</strong></span>

      <div class="bar-track">
        <span class="bar-fill left-fill" :style="{ width: leftWidth }" />
        <span class="bar-fill right-fill" :style="{ width: rightWidth }" />
      </div>

      <span class="comparison-side comparison-side-right"><strong>{{ rightValue }}</strong> {{ rightLabel }}</span>
    </div>
  </div>
</template>

<style scoped>
.comparison-bar {
  display: grid;
  gap: 0.35rem;
}

.comparison-row {
  display: grid;
  grid-template-columns: minmax(0, auto) minmax(0, 1fr) minmax(0, auto);
  gap: 0.75rem;
  align-items: center;
}

.comparison-side {
  font-size: 0.85rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.comparison-title {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-subtle);
  text-align: center;
}

.bar-track {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.35rem;
}

.bar-fill {
  display: block;
  height: 0.7rem;
  border-radius: 999px;
}

.left-fill {
  justify-self: end;
  background: linear-gradient(90deg, rgba(217, 151, 0, 0.45), var(--accent));
}

.right-fill {
  background: linear-gradient(90deg, var(--brand-cool), rgba(137, 190, 229, 0.45));
}

@media (max-width: 640px) {
  .comparison-row {
    grid-template-columns: 1fr;
    gap: 0.45rem;
  }

  .comparison-side,
  .comparison-side-left,
  .comparison-side-right {
    text-align: center;
  }
}
</style>
