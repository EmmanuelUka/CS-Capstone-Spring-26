<script setup>
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
      <span class="brand-badge">HM</span>
      <div>
        <p class="eyebrow">Hashmark Recruiting Assistant</p>
        <h1>Coach Command Center</h1>
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
  padding: 1rem;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    radial-gradient(circle at top left, rgba(255, 183, 94, 0.14), transparent 32%),
    rgba(23, 19, 24, 0.88);
}

.brand-badge {
  display: grid;
  place-items: center;
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 20px;
  background: linear-gradient(135deg, #ffb75e, #ff7d54);
  color: #1b1512;
  font-weight: 900;
}

.eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(242, 236, 227, 0.56);
}

.brand-panel h1 {
  margin: 0.28rem 0 0;
  font-size: 1.45rem;
  letter-spacing: -0.04em;
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
  background: rgba(255, 255, 255, 0.05);
  color: rgba(242, 236, 227, 0.74);
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
  background: linear-gradient(135deg, rgba(255, 183, 94, 0.12), rgba(121, 200, 255, 0.1));
  color: #f2ece3;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
}

.nav-link.active {
  background: linear-gradient(135deg, rgba(255, 183, 94, 0.2), rgba(121, 200, 255, 0.12));
  color: #f2ece3;
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
