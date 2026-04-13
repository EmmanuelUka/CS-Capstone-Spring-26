<script setup>
import hashmarkLogo from '../assets/hashmark-logo.svg'

defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  currentPath: {
    type: String,
    default: '/dashboard',
  },
})

const emit = defineEmits(['navigate'])

function isActive(itemPath, currentPath) {
  return currentPath === itemPath || currentPath.startsWith(`${itemPath}/`)
}
</script>

<template>
  <header class="top-menu">
    <div class="brand-panel">
      <span class="brand-badge">
        <img :src="hashmarkLogo" alt="Hashmark logo" />
      </span>
      <div class="brand-copy">
        <h1>Hashmark</h1>
        <p class="brand-subtitle">Recruiting Assistant</p>
      </div>
    </div>

    <nav class="nav-strip" aria-label="Primary">
      <button
        v-for="item in items"
        :key="item.path"
        class="nav-link"
        :class="{ active: isActive(item.path, currentPath) }"
        type="button"
        @click="emit('navigate', item.path)"
      >
        <span>{{ item.icon }}</span>
        {{ item.label }}
      </button>
    </nav>
  </header>
</template>

<style scoped>
.top-menu {
  display: grid;
  gap: 1rem;
  margin-bottom: 1rem;
}

.brand-panel {
  display: flex;
  gap: 0.9rem;
  align-items: center;
  padding: 1rem 0 1rem 1rem;
  border-radius: 28px;
  border: 1px solid var(--line);
  background:
    radial-gradient(circle at top left, rgba(217, 151, 0, 0.14), transparent 32%),
    rgba(10, 27, 58, 0.88);
}

.brand-badge {
  display: grid;
  place-items: center;
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 20px;
  background: linear-gradient(135deg, var(--accent), var(--accent-strong));
  padding: 0.55rem;
}

.brand-badge img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: brightness(0.12);
}

.brand-copy {
  flex: 0 1 auto;
  min-width: 0;
}

.brand-panel h1 {
  margin: 0;
  font-size: 1.45rem;
  letter-spacing: -0.04em;
  line-height: 1.05;
}

.brand-subtitle {
  margin: 0.25rem 0 0;
  color: var(--text-subtle);
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.nav-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.nav-link {
  display: inline-flex;
  gap: 0.55rem;
  justify-content: center;
  align-items: center;
  min-height: 3rem;
  padding: 0.9rem 1rem;
  border-radius: 18px;
  background: var(--bg-soft);
  color: var(--text-muted);
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.nav-link:hover {
  transform: translateY(-2px);
  background: linear-gradient(135deg, rgba(217, 151, 0, 0.15), rgba(79, 110, 247, 0.14));
  color: var(--text);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
}

.nav-link.active {
  background: linear-gradient(135deg, rgba(217, 151, 0, 0.24), rgba(79, 110, 247, 0.18));
  color: var(--text);
}

@media (min-width: 880px) {
  .top-menu {
    grid-template-columns: 320px minmax(0, 1fr);
    align-items: stretch;
  }

  .nav-strip {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }
}
</style>
