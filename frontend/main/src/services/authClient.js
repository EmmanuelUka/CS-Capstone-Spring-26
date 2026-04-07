const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

function resolveUrl(path) {
  return API_BASE ? `${API_BASE}${path}` : path
}

async function request(path, options = {}) {
  const response = await fetch(resolveUrl(path), {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    let message = 'Request failed.'

    try {
      const payload = await response.json()
      message = payload?.error || message
    } catch {
      message = response.statusText || message
    }

    throw new Error(message)
  }

  const contentType = response.headers.get('content-type') || ''
  return contentType.includes('application/json') ? response.json() : null
}

export async function getCsrfToken() {
  const payload = await request('/api/csrf', { method: 'GET' })
  return payload?.csrfToken || ''
}

export async function getCurrentUser() {
  const payload = await request('/api/me', { method: 'GET' })
  return payload?.email ? payload : null
}

export function loginWithMicrosoft() {
  const loginUrl = new URL(resolveUrl('/auth/microsoft/login'), window.location.origin)
  loginUrl.searchParams.set('return_to', window.location.origin)
  window.location.href = loginUrl.toString()
}

export async function logoutSession(csrfToken) {
  return request('/auth/logout', {
    method: 'POST',
    headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
    body: JSON.stringify({}),
  })
}
