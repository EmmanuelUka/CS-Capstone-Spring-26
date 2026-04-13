<script setup>
import { computed } from 'vue'

const props = defineProps({
  authBusy: {
    type: Boolean,
    default: false,
  },
  authLoading: {
    type: Boolean,
    default: false,
  },
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
  user: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['login', 'logout'])

const buttonLabel = computed(() => {
  if (props.authLoading) {
    return 'Checking session...'
  }

  if (props.authBusy) {
    return 'Working...'
  }

  return props.isAuthenticated ? 'Logout' : 'Login'
})

const helperText = computed(() => {
  if (props.authLoading) {
    return 'Connecting to authentication service'
  }

  if (props.isAuthenticated) {
    const role = props.user?.role || 'User'
    const name = props.user?.name || props.user?.email || 'Signed in'
    return `${name} • ${role}`
  }

  return 'Microsoft sign-in'
})

function handleClick() {
  if (props.authLoading || props.authBusy) {
    return
  }

  emit(props.isAuthenticated ? 'logout' : 'login')
}
</script>

<template>
  <button class="auth-button" type="button" :disabled="authBusy || authLoading" @click="handleClick">
    <span class="button-label">{{ buttonLabel }}</span>
    <span class="button-helper">{{ helperText }}</span>
  </button>
</template>

<style scoped>
.auth-button {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
  min-width: 11.5rem;
  padding: 0.95rem 1.15rem;
  border: 1px solid rgba(255, 233, 194, 0.14);
  border-radius: 1.15rem;
  background:
    linear-gradient(135deg, rgba(255, 195, 111, 0.22), rgba(255, 129, 76, 0.16)),
    rgba(44, 29, 22, 0.9);
  color: var(--text);
  box-shadow: 0 18px 38px rgba(0, 0, 0, 0.22);
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.auth-button:hover:enabled {
  transform: translateY(-2px);
  border-color: rgba(255, 194, 118, 0.34);
  box-shadow: 0 22px 44px rgba(0, 0, 0, 0.28);
}

.auth-button:disabled {
  cursor: progress;
  opacity: 0.74;
}

.button-label {
  font-size: 1rem;
  font-weight: 700;
}

.button-helper {
  font-size: 0.78rem;
  color: var(--text-subtle);
}
</style>
