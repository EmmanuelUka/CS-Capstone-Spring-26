<script setup>
import { computed } from 'vue'

import { useBackendObject } from '../composables/useBackendObject'
import { resolveBackendObjectUrl } from '../services/backendObjectClient'

const props = defineProps({
  title: {
    type: String,
    default: 'Backend object hook',
  },
  description: {
    type: String,
    default: 'Fetches a JSON object from Flask so you have a single place to wire frontend views into backend data.',
  },
  endpoint: {
    type: String,
    default: '/api/demo-object',
  },
})

const { data, error, loading, lastLoadedAt, load } = useBackendObject({
  endpoint: props.endpoint,
})

const payloadText = computed(() => {
  if (!data.value) {
    return ''
  }

  return JSON.stringify(data.value, null, 2)
})

const resolvedUrl = computed(() => resolveBackendObjectUrl(props.endpoint))

const statusText = computed(() => {
  if (loading.value) {
    return 'Loading'
  }

  if (error.value) {
    return 'Error'
  }

  if (data.value) {
    return 'Connected'
  }

  return 'Idle'
})

const lastLoadedText = computed(() => {
  if (!lastLoadedAt.value) {
    return 'Not loaded yet'
  }

  return new Date(lastLoadedAt.value).toLocaleTimeString()
})

function refreshObject() {
  load().catch(() => {})
}
</script>

<template>
  <section class="backend-object surface-panel">
    <div class="backend-object-header">
      <div class="backend-object-copy">
        <p class="section-label">Backend Bridge</p>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>

      <button class="ghost-button backend-object-button" type="button" :disabled="loading" @click="refreshObject">
        {{ loading ? 'Loading...' : 'Refresh object' }}
      </button>
    </div>

    <div class="backend-object-meta">
      <article class="backend-object-chip">
        <span>Endpoint</span>
        <strong>{{ endpoint }}</strong>
      </article>

      <article class="backend-object-chip">
        <span>Resolved URL</span>
        <strong>{{ resolvedUrl }}</strong>
      </article>

      <article class="backend-object-chip">
        <span>Status</span>
        <strong>{{ statusText }}</strong>
      </article>
    </div>

    <p class="backend-object-note">
      Change the <code>endpoint</code> prop or set <code>VITE_OBJECT_API_URL</code> to point this at a different Flask
      route.
    </p>

    <p v-if="error" class="backend-object-error">{{ error }}</p>
    <pre v-else-if="payloadText" class="backend-object-code">{{ payloadText }}</pre>
    <div v-else class="backend-object-empty">Waiting for backend data.</div>

    <p class="backend-object-footer">Last loaded: {{ lastLoadedText }}</p>
  </section>
</template>

<style scoped>
.backend-object {
  gap: 1rem;
}

.backend-object-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}

.backend-object-copy,
.backend-object-meta {
  display: grid;
  gap: 0.85rem;
}

.backend-object-copy h2,
.backend-object-copy p,
.backend-object-footer,
.backend-object-note,
.backend-object-error {
  margin: 0;
}

.backend-object-copy h2 {
  font-size: clamp(1.3rem, 2vw, 1.8rem);
}

.backend-object-copy > p:last-child,
.backend-object-note,
.backend-object-footer {
  color: var(--text-muted);
}

.backend-object-button {
  min-width: 11rem;
}

.backend-object-meta {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.backend-object-chip {
  display: grid;
  gap: 0.35rem;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.04);
}

.backend-object-chip span {
  color: var(--text-subtle);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.backend-object-chip strong {
  overflow-wrap: anywhere;
}

.backend-object-code,
.backend-object-empty,
.backend-object-error {
  padding: 1rem;
  border-radius: 20px;
  border: 1px solid var(--line);
  background: rgba(7, 14, 27, 0.72);
}

.backend-object-code {
  margin: 0;
  overflow-x: auto;
  color: var(--success);
  font-size: 0.9rem;
}

.backend-object-empty {
  color: var(--text-muted);
}

.backend-object-error {
  color: #ffb3b3;
}

@media (max-width: 720px) {
  .backend-object-header {
    flex-direction: column;
  }

  .backend-object-button {
    width: 100%;
  }
}
</style>
