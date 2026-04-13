<script setup>
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import AuthView from './views/AuthView.vue'
import TopMenuBar from './components/TopMenuBar.vue'
import { useAuthSession } from './composables/useAuthSession'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '◉' },
  { path: '/players', label: 'Players', icon: '▦' },
  { path: '/compare', label: 'Compare', icon: '⇄' },
  { path: '/shortlists', label: 'Shortlists', icon: '★' },
  { path: '/schemes', label: 'Schemes', icon: '◇' },
  { path: '/account', label: 'Account', icon: '⚙' },
]

const router = useRouter()
const route = useRoute()
const { loading, authBusy, status, user, isAuthenticated, login, logout } = useAuthSession()

const currentPath = computed(() => route.path)

function go(path) {
  router.push(path)
}
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell-auth': !isAuthenticated }">
    <div v-if="loading" class="auth-loading surface-panel">
      <p class="section-label">Hashmark</p>
      <h2>Checking your session...</h2>
      <p>Loading your recruiting workspace.</p>
    </div>

    <AuthView
      v-else-if="!isAuthenticated"
      :status="status"
      :auth-busy="authBusy"
      @login="login"
    />

    <div v-else class="page-wrap">
      <TopMenuBar
        :items="navItems"
        :current-path="currentPath"
        @navigate="go"
      />

      <main class="content-shell">
        <RouterView v-slot="{ Component }">
          <component :is="Component" :user="user" :auth-busy="authBusy" @logout="logout" />
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: 0 0 2rem;
}

.app-shell-auth {
  display: grid;
  place-items: center;
  padding: 1.5rem;
}

.page-wrap {
  width: min(1380px, calc(100% - 1.2rem));
  margin: 0 auto;
  padding-top: 1rem;
}

.content-shell {
  display: grid;
}

.auth-loading {
  width: min(32rem, 100%);
  padding: 2rem;
  text-align: center;
}

.auth-loading h2 {
  margin: 0;
  font-size: clamp(1.9rem, 4vw, 2.6rem);
}

.auth-loading p:last-child {
  margin: 0;
  color: var(--text-muted);
}

@media (min-width: 720px) {
  .page-wrap {
    width: min(1380px, calc(100% - 2rem));
  }
}
</style>
