import { beginRequest, endRequest } from '../composables/useRequestState'

const objectApiBaseEnv = import.meta.env.VITE_OBJECT_API_URL
const OBJECT_API_BASE = (objectApiBaseEnv === undefined ? 'http://localhost:5001' : objectApiBaseEnv).replace(
  /\/$/,
  ''
)

export const DEFAULT_OBJECT_ENDPOINT = import.meta.env.VITE_OBJECT_ENDPOINT || '/api/demo-object'

export function resolveBackendObjectUrl(path = DEFAULT_OBJECT_ENDPOINT) {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return OBJECT_API_BASE ? `${OBJECT_API_BASE}${normalizedPath}` : normalizedPath
}

export async function fetchBackendObject(path = DEFAULT_OBJECT_ENDPOINT, options = {}) {
  beginRequest()

  try {
    const response = await fetch(resolveBackendObjectUrl(path), {
      method: 'GET',
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
    })

    if (!response.ok) {
      let message = 'Unable to load backend object.'

      try {
        const payload = await response.json()
        message = payload?.error || payload?.message || message
      } catch {
        message = response.statusText || message
      }

      throw new Error(message)
    }

    const contentType = response.headers.get('content-type') || ''

    if (!contentType.includes('application/json')) {
      throw new Error('Expected a JSON response from the backend.')
    }

    return response.json()
  } finally {
    endRequest()
  }
}
