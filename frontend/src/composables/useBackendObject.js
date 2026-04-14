import { onMounted, ref } from 'vue'

import { DEFAULT_OBJECT_ENDPOINT, fetchBackendObject } from '../services/backendObjectClient'

export function useBackendObject(options = {}) {
  const endpoint = options.endpoint || DEFAULT_OBJECT_ENDPOINT
  const requestOptions = options.requestOptions || {}
  const immediate = options.immediate !== false

  const data = ref(null)
  const error = ref('')
  const loading = ref(false)
  const lastLoadedAt = ref('')

  async function load(override = {}) {
    const nextEndpoint = override.endpoint || endpoint
    const nextRequestOptions = {
      ...requestOptions,
      ...(override.requestOptions || {}),
    }

    loading.value = true
    error.value = ''

    try {
      const payload = await fetchBackendObject(nextEndpoint, nextRequestOptions)
      data.value = payload
      lastLoadedAt.value = new Date().toISOString()
      return payload
    } catch (requestError) {
      error.value = requestError.message || 'Unable to load backend object.'
      throw requestError
    } finally {
      loading.value = false
    }
  }

  if (immediate) {
    onMounted(() => {
      load().catch(() => {})
    })
  }

  return {
    endpoint,
    data,
    error,
    loading,
    lastLoadedAt,
    load,
  }
}
