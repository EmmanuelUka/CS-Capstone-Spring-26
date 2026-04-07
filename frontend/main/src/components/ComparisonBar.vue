<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true,
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
    <div class="comparison-meta">
      <span>{{ leftLabel }} <strong>{{ leftValue }}</strong></span>
      <span class="comparison-title">{{ label }}</span>
      <span><strong>{{ rightValue }}</strong> {{ rightLabel }}</span>
    </div>

    <div class="bar-track">
      <span class="bar-fill left-fill" :style="{ width: leftWidth }" />
      <span class="bar-fill right-fill" :style="{ width: rightWidth }" />
    </div>
  </div>
</template>

<style scoped>
.comparison-bar {
  display: grid;
  gap: 0.6rem;
}

.comparison-meta {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 0.75rem;
  align-items: center;
  font-size: 0.85rem;
  color: rgba(242, 236, 227, 0.7);
}

.comparison-meta span:last-child {
  text-align: right;
}

.comparison-title {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(242, 236, 227, 0.52);
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
  background: linear-gradient(90deg, rgba(255, 183, 94, 0.45), #ffb75e);
}

.right-fill {
  background: linear-gradient(90deg, #79c8ff, rgba(121, 200, 255, 0.45));
}
</style>
