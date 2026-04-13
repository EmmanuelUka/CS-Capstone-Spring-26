<script setup>
import hashmarkLogo from '../assets/hashmark-logo.svg'

defineProps({
  status: {
    type: String,
    default: '',
  },
  authBusy: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['login'])
</script>

<template>
  <section class="auth-shell">
    <div class="auth-grid surface-panel">
      <div class="auth-copy">
        <p class="section-label">Hashmark Recruiting Assistant</p>
        <h1>Sign in to open your recruiting dashboard.</h1>
        <p class="auth-lead">
          Keep the main command center experience, but start with a clean Microsoft login flow for your coaching
          staff.
        </p>

        <div class="auth-highlights">
          <article>
            <strong>Board visibility</strong>
            <p>Track evaluations, comparisons, and shortlist movement from one place.</p>
          </article>
          <article>
            <strong>Secure access</strong>
            <p>Use your approved Microsoft account to enter the workspace.</p>
          </article>
        </div>
      </div>

      <div class="auth-card">
        <div class="auth-badge">
          <img :src="hashmarkLogo" alt="Hashmark logo" />
        </div>
        <h2>Welcome back</h2>
        <p>Continue with Microsoft to enter the coach command center.</p>

        <button class="primary-button auth-button" type="button" :disabled="authBusy" @click="$emit('login')">
          {{ authBusy ? 'Redirecting...' : 'Sign in with Microsoft' }}
        </button>

        <p v-if="status" class="auth-status">{{ status }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.auth-shell {
  width: min(1120px, 100%);
}

.auth-grid {
  grid-template-columns: minmax(0, 1.2fr);
  gap: 1.25rem;
  padding: 1.25rem;
}

.auth-copy,
.auth-card,
.auth-highlights,
.auth-highlights article {
  display: grid;
  gap: 0.85rem;
}

.auth-copy {
  padding: clamp(1rem, 3vw, 2rem);
}

.auth-copy h1,
.auth-card h2 {
  margin: 0;
}

.auth-copy h1 {
  font-size: clamp(2.3rem, 5vw, 4.25rem);
  line-height: 0.98;
  letter-spacing: -0.06em;
}

.auth-lead,
.auth-card p {
  margin: 0;
  color: var(--text-muted);
}

.auth-highlights {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  margin-top: 0.5rem;
}

.auth-highlights article {
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--bg-soft);
}

.auth-highlights strong {
  font-size: 1rem;
}

.auth-card {
  align-content: start;
  padding: clamp(1.2rem, 3vw, 2rem);
  border: 1px solid var(--line);
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(217, 151, 0, 0.12), transparent 28%),
    rgba(8, 24, 53, 0.74);
  box-shadow: var(--shadow-md);
}

.auth-badge {
  display: grid;
  place-items: center;
  width: 3.6rem;
  height: 3.6rem;
  border-radius: 1.2rem;
  background: linear-gradient(135deg, var(--accent), var(--accent-strong));
  padding: 0.55rem;
}

.auth-badge img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: brightness(0.12);
}

.auth-button {
  width: 100%;
  margin-top: 0.4rem;
}

.auth-button:disabled {
  opacity: 0.72;
  cursor: progress;
}

.auth-status {
  min-height: 1.5rem;
  color: var(--brand-cool);
}

@media (min-width: 900px) {
  .auth-grid {
    grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
    align-items: stretch;
    padding: 1.5rem;
  }

  .auth-card {
    align-self: stretch;
  }
}
</style>
