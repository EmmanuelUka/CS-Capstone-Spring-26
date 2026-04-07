import { computed, onMounted, onUnmounted, ref } from 'vue'

function parseHash() {
  const raw = window.location.hash.replace(/^#/, '') || '/dashboard'
  const [path, search = ''] = raw.split('?')
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const segments = cleanPath.split('/').filter(Boolean)
  const query = new URLSearchParams(search)

  return {
    path: cleanPath,
    segments,
    query,
  }
}

export function useHashRoute() {
  const route = ref(parseHash())

  function syncRoute() {
    route.value = parseHash()
  }

  function go(path) {
    const nextPath = path.startsWith('/') ? path : `/${path}`
    if (window.location.hash === `#${nextPath}`) {
      syncRoute()
      return
    }
    window.location.hash = nextPath
  }

  onMounted(() => {
    if (!window.location.hash) {
      window.location.hash = '/dashboard'
    }

    syncRoute()
    window.addEventListener('hashchange', syncRoute)
  })

  onUnmounted(() => {
    window.removeEventListener('hashchange', syncRoute)
  })

  const currentPath = computed(() => route.value.path)

  return {
    route,
    currentPath,
    go,
  }
}
