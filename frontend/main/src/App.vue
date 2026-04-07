<script setup>
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import TopMenuBar from './components/TopMenuBar.vue'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '◉' },
  { path: '/players', label: 'Players', icon: '▦' },
  { path: '/compare', label: 'Compare', icon: '⇄' },
  { path: '/shortlists', label: 'Shortlists', icon: '★' },
]

const router = useRouter()
const route = useRoute()

const currentPath = computed(() => route.path)

function go(path) {
  router.push(path)
}
</script>

<template>
  <div class="app-shell">
    <div class="page-wrap">
      <TopMenuBar :items="navItems" :current-path="currentPath" @navigate="go" />

      <main class="content-shell">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: 0 0 2rem;
}

.page-wrap {
  width: min(1380px, calc(100% - 1.2rem));
  margin: 0 auto;
  padding-top: 1rem;
}

.content-shell {
  display: grid;
}

@media (min-width: 720px) {
  .page-wrap {
    width: min(1380px, calc(100% - 2rem));
  }
}
</style>
