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
  valueDisplay: {
    type: [String, Number],
    default: null,
  },
})

const total = computed(() => Math.max(props.leftValue + props.rightValue, 1))
const leftWidth = computed(() => `${(props.leftValue / total.value) * 100}%`)
</script>

<template>
  <div class="comparison-bar">
    <div v-if="label" class="comparison-title">{{ label }}</div>

    <div class="comparison-row">
      <span class="comparison-side comparison-side-left">{{ leftLabel }}</span>

      <div class="bar-track">
        <span class="bar-fill left-fill" :style="{ width: leftWidth }" />
      </div>

      <span v-if="valueDisplay !== null || rightLabel" class="comparison-side comparison-side-right">
        <strong>{{ valueDisplay ?? rightValue }}</strong><template v-if="rightLabel"> {{ rightLabel }}</template>
      </span>
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
  grid-template-columns: 7rem minmax(0, 1fr) 3rem;
  gap: 0.75rem;
  align-items: center;
}

.comparison-side {
  font-size: 0.85rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.comparison-side-left {
  font-weight: 800;
}

.comparison-side-right {
  text-align: right;
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
  position: relative;
  height: 0.7rem;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.08);
}

.bar-fill {
  display: block;
  height: 0.7rem;
  border-radius: 999px;
}

.left-fill {
  background: linear-gradient(90deg, rgba(217, 151, 0, 0.45), var(--accent));
  box-shadow: 0 0 0 1px rgba(217, 151, 0, 0.14) inset;
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
