import { computed, reactive } from 'vue'

const requestState = reactive({
  pendingCount: 0,
})

export function beginRequest() {
  requestState.pendingCount += 1
}

export function endRequest() {
  requestState.pendingCount = Math.max(0, requestState.pendingCount - 1)
}

export function useRequestState() {
  return {
    pendingCount: computed(() => requestState.pendingCount),
    isRequestPending: computed(() => requestState.pendingCount > 0),
  }
}
