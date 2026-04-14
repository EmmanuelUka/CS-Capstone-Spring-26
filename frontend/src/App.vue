<script setup>
import { computed, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import AuthView from './views/AuthView.vue'
import TopMenuBar from './components/TopMenuBar.vue'
import { useAuthSession } from './composables/useAuthSession'
import { useRequestState } from './composables/useRequestState'
import { useRecruitingStore } from './store/useRecruitingStore'

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
const { isRequestPending } = useRequestState()
const { ensureExampleDataLoaded } = useRecruitingStore()

const currentPath = computed(() => route.path)

function go(path) {
  router.push(path)
}

watch(
  isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      ensureExampleDataLoaded()
    }
  },
  { immediate: true }
)
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
      <transition name="request-whirler">
        <div v-if="isRequestPending" class="request-whirler" aria-live="polite" aria-label="Loading">
          <span class="request-whirler-spinner" />
          <span>Loading</span>
        </div>
      </transition>

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

.request-whirler {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 120;
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 3rem;
  padding: 0.75rem 0.95rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.14), rgba(255, 255, 255, 0.03)),
    rgba(9, 17, 31, 0.92);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(18px);
  color: var(--text);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.request-whirler-spinner {
  width: 1rem;
  height: 1rem;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.18);
  border-top-color: var(--accent-strong);
  animation: whirler-spin 0.8s linear infinite;
}

.request-whirler-enter-active,
.request-whirler-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.request-whirler-enter-from,
.request-whirler-leave-to {
  opacity: 0;
  transform: translateY(-0.35rem);
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

@keyframes whirler-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
