<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <header class="page-header">
    <div class="copy-block">
      <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="page-copy">{{ description }}</p>
    </div>

    <div v-if="$slots.actions" class="header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  align-items: end;
  margin-bottom: 1.8rem;
}

.copy-block {
  max-width: 42rem;
}

.eyebrow {
  margin: 0 0 0.45rem;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
}

h1 {
  margin: 0;
  font-size: clamp(2.4rem, 4.4vw, 4.6rem);
  line-height: 0.92;
  letter-spacing: -0.045em;
  max-width: 12ch;
}

.page-copy {
  margin: 1rem 0 0;
  color: var(--text-muted);
  line-height: 1.65;
  max-width: 42rem;
}

.header-actions {
  flex-shrink: 0;
}

@media (max-width: 760px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
