import { computed, onMounted, ref } from 'vue'

import { getCsrfToken, getCurrentUser, loginWithMicrosoft, logoutSession } from '../services/authClient'

export function useAuthSession() {
  const loading = ref(true)
  const authBusy = ref(false)
  const status = ref('')
  const user = ref(null)
  const csrfToken = ref('')

  const isAuthenticated = computed(() => Boolean(user.value?.email))

  function consumeAuthErrorFromUrl() {
    const params = new URLSearchParams(window.location.search)
    const authError = params.get('auth_error')
    const authDenied = params.get('auth')

    const messages = {
      invalid_state: 'Login failed. Please try again.',
      missing_code: 'Login failed. Please try again.',
      token_failed: 'Login failed while signing in.',
      graph_timeout: 'Microsoft took too long to respond.',
      graph_failed: 'Login failed while contacting Microsoft.',
      domain_not_allowed: 'Access denied for this email domain.',
      access_not_granted: 'Access not granted. Contact your administrator.',
    }

    if (authError) {
      status.value = messages[authError] || 'Login failed. Please try again.'
      params.delete('auth_error')
    } else if (authDenied === 'denied') {
      status.value = 'Access denied. Contact your administrator.'
      params.delete('auth')
    }

    if (!authError && authDenied !== 'denied') {
      return
    }

    const nextQuery = params.toString()
    const nextUrl =
      window.location.pathname +
      (nextQuery ? `?${nextQuery}` : '') +
      window.location.hash

    window.history.replaceState({}, '', nextUrl)
  }

  async function refreshSession() {
    loading.value = true

    try {
      const [csrf, me] = await Promise.all([getCsrfToken(), getCurrentUser()])
      csrfToken.value = csrf
      user.value = me
    } catch {
      csrfToken.value = ''
      user.value = null
    } finally {
      loading.value = false
    }
  }

  function login() {
    loginWithMicrosoft()
  }

  async function logout() {
    authBusy.value = true
    status.value = ''

    try {
      await logoutSession(csrfToken.value)
      status.value = 'Signed out successfully.'
      await refreshSession()
    } catch (error) {
      status.value = error.message || 'Unable to sign out right now.'
    } finally {
      authBusy.value = false
    }
  }

  onMounted(() => {
    consumeAuthErrorFromUrl()
    refreshSession()
  })

  return {
    loading,
    authBusy,
    status,
    user,
    isAuthenticated,
    refreshSession,
    login,
    logout,
  }
}
