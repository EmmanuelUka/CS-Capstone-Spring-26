<script setup>
import { computed, onMounted, ref } from 'vue'

import {
  createManagedUser,
  deleteManagedUser,
  getCsrfToken,
  getManagedUsers,
  updateManagedUserRole,
} from '../services/authClient'

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
  authBusy: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['logout'])

const csrfToken = ref('')
const commandBusy = ref(false)
const addBusy = ref(false)
const usersLoading = ref(false)
const addEmail = ref('')
const addRole = ref('COACH')
const addStatus = ref('')
const directoryStatus = ref('')
const users = ref([])

const isSuperAdmin = computed(() => props.user?.role === 'SUPER_ADMIN')
const isAdmin = computed(() => props.user?.role === 'ADMIN')
const isAdminOrSuper = computed(() => isAdmin.value || isSuperAdmin.value)

function isSelf(account) {
  return (account?.email || '').toLowerCase() === (props.user?.email || '').toLowerCase()
}

function canDelete(account) {
  if (isSelf(account)) return false
  const role = (account?.role || '').toUpperCase()
  if (isSuperAdmin.value) return role !== 'SUPER_ADMIN'
  if (isAdmin.value) return role === 'COACH'
  return false
}

function canPromote(account) {
  if (!isSuperAdmin.value || isSelf(account)) return false
  return (account?.role || '').toUpperCase() === 'COACH'
}

function canDemote(account) {
  if (!isSuperAdmin.value || isSelf(account)) return false
  return (account?.role || '').toUpperCase() === 'ADMIN'
}

async function refreshCsrf() {
  csrfToken.value = await getCsrfToken()
}

async function loadUsers() {
  if (!isAdminOrSuper.value) {
    users.value = []
    return
  }

  usersLoading.value = true
  directoryStatus.value = ''

  try {
    users.value = await getManagedUsers()
  } catch (error) {
    directoryStatus.value = error.message || 'Unable to load the user directory.'
  } finally {
    usersLoading.value = false
  }
}

async function addUser() {
  if (!addEmail.value.trim()) {
    addStatus.value = 'Enter an email first.'
    return
  }

  addBusy.value = true
  addStatus.value = 'Adding account...'

  try {
    const payload = await createManagedUser(
      {
        email: addEmail.value.trim().toLowerCase(),
        role: addRole.value,
      },
      csrfToken.value
    )

    if (payload?.status === 'user_exists') {
      addStatus.value = 'That account already has access.'
    } else {
      addStatus.value =
        addRole.value === 'ADMIN' ? 'Admin account created.' : 'Coach account created.'
      addEmail.value = ''
      addRole.value = 'COACH'
    }

    await loadUsers()
  } catch (error) {
    addStatus.value = error.message || 'Unable to add that account.'
  } finally {
    addBusy.value = false
  }
}

async function removeUser(email) {
  commandBusy.value = true
  directoryStatus.value = ''

  try {
    await deleteManagedUser({ email }, csrfToken.value)
    directoryStatus.value = 'Account removed.'
    await loadUsers()
  } catch (error) {
    directoryStatus.value = error.message || 'Unable to remove that account.'
  } finally {
    commandBusy.value = false
  }
}

async function setRole(email, role) {
  commandBusy.value = true
  directoryStatus.value = ''

  try {
    await updateManagedUserRole({ email, role }, csrfToken.value)
    directoryStatus.value = role === 'ADMIN' ? 'Account promoted to ADMIN.' : 'Account changed to COACH.'
    await loadUsers()
  } catch (error) {
    directoryStatus.value = error.message || 'Unable to change that role.'
  } finally {
    commandBusy.value = false
  }
}

onMounted(async () => {
  await refreshCsrf()
  await loadUsers()
})
</script>

<template>
  <section class="account-grid">
    <section class="identity-panel surface-panel">
      <p class="section-label">Account</p>
      <h2>You are signed in as {{ user?.name || 'Hashmark user' }}.</h2>
      <p class="identity-copy">
        Your session is active and tied to the email and role shown below. Use this page to confirm access and manage
        account-level actions.
      </p>

      <div class="identity-cards">
        <article class="identity-card">
          <span>Email</span>
          <strong>{{ user?.email || 'Unavailable' }}</strong>
        </article>
        <article class="identity-card">
          <span>Role</span>
          <strong>{{ user?.role || 'Unknown' }}</strong>
        </article>
        <article class="identity-card">
          <span>Access</span>
          <strong>{{ isAdminOrSuper ? 'Management enabled' : 'Standard user' }}</strong>
        </article>
      </div>

      <div class="identity-actions">
        <button class="primary-button" type="button" :disabled="authBusy" @click="emit('logout')">
          {{ authBusy ? 'Signing out...' : 'Sign out' }}
        </button>
      </div>
    </section>

    <section v-if="isAdminOrSuper" class="command-panel surface-panel">
      <div class="panel-header">
        <div>
          <p class="section-label">Command Panel</p>
          <h3>{{ isSuperAdmin ? 'Admin and access controls' : 'Coach access controls' }}</h3>
        </div>
      </div>

      <p class="command-copy">
        <template v-if="isSuperAdmin">
          Super admins can create coach or admin accounts, promote coaches to admin, demote admins, and remove any
          non-super-admin account.
        </template>
        <template v-else>
          Admins can grant coach access and remove coach accounts. Admin role changes stay locked to super admins.
        </template>
      </p>

      <div class="form-grid">
        <input v-model="addEmail" type="email" placeholder="user@kent.edu" />
        <select v-model="addRole">
          <option value="COACH">COACH</option>
          <option v-if="isSuperAdmin" value="ADMIN">ADMIN</option>
        </select>
        <button class="primary-button" type="button" :disabled="addBusy" @click="addUser">
          {{ addBusy ? 'Adding...' : 'Grant access' }}
        </button>
      </div>

      <p class="feedback-line">{{ addStatus }}</p>

      <div class="directory-panel">
        <div class="directory-header">
          <h4>User Directory</h4>
          <button class="ghost-button" type="button" :disabled="usersLoading || commandBusy" @click="loadUsers">
            {{ usersLoading ? 'Refreshing...' : 'Refresh list' }}
          </button>
        </div>

        <p v-if="usersLoading" class="feedback-line">Loading accounts...</p>

        <div v-else class="users-table">
          <div class="users-head">
            <span>Email</span>
            <span>Role</span>
            <span>Actions</span>
          </div>

          <div v-for="account in users" :key="account.email" class="users-row">
            <span class="mono">{{ account.email }}</span>
            <span>{{ account.role }}</span>
            <span class="row-actions">
              <button
                v-if="canPromote(account)"
                class="ghost-button mini-button"
                type="button"
                :disabled="commandBusy"
                @click="setRole(account.email, 'ADMIN')"
              >
                Make admin
              </button>
              <button
                v-if="canDemote(account)"
                class="ghost-button mini-button"
                type="button"
                :disabled="commandBusy"
                @click="setRole(account.email, 'COACH')"
              >
                Make coach
              </button>
              <button
                v-if="canDelete(account)"
                class="danger-button mini-button"
                type="button"
                :disabled="commandBusy"
                @click="removeUser(account.email)"
              >
                Remove access
              </button>
            </span>
          </div>
        </div>

        <p class="feedback-line">{{ directoryStatus }}</p>
      </div>
    </section>
  </section>
</template>

<style scoped>
.account-grid {
  display: grid;
  gap: 1rem;
}

.identity-panel,
.command-panel,
.identity-cards,
.directory-panel {
  display: grid;
  gap: 1rem;
}

.identity-panel {
  padding: 1.2rem;
  align-self: start;
}

.identity-panel h2,
.panel-header h3,
.directory-header h4 {
  margin: 0;
}

.identity-copy,
.command-copy,
.feedback-line {
  margin: 0;
  color: var(--text-muted);
}

.identity-cards {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.identity-card,
.users-table,
.users-row,
.users-head,
.directory-panel,
.form-grid input,
.form-grid select {
  border: 1px solid var(--line);
}

.identity-card,
.directory-panel {
  padding: 1rem;
  border-radius: 22px;
  background: var(--bg-soft);
}

.identity-card span {
  color: var(--text-subtle);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.identity-card strong {
  display: block;
  margin-top: 0.4rem;
  word-break: break-word;
}

.identity-actions {
  display: flex;
  justify-content: flex-start;
}

.panel-header,
.directory-header,
.users-head,
.users-row {
  display: grid;
  gap: 0.8rem;
  align-items: center;
}

.form-grid {
  display: grid;
  gap: 0.75rem;
}

.form-grid input,
.form-grid select {
  min-height: 3rem;
  padding: 0.8rem 0.95rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
}

.form-grid select option {
  color: #102445;
}

.users-table {
  overflow: hidden;
  border-radius: 20px;
}

.users-head,
.users-row {
  grid-template-columns: 1.5fr 0.7fr 1.5fr;
  padding: 0.95rem 1rem;
}

.users-head {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.76rem;
}

.users-row {
  border-top: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.03);
}

.mono {
  word-break: break-word;
}

.row-actions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.mini-button,
.danger-button {
  min-height: 2.35rem;
  padding: 0.6rem 0.85rem;
  border-radius: 14px;
  font-weight: 700;
  cursor: pointer;
}

.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: #ffd7d7;
}

@media (min-width: 980px) {
  .account-grid {
    grid-template-columns: minmax(320px, 0.85fr) minmax(0, 1.15fr);
    align-items: start;
  }

  .identity-panel {
    max-width: 28rem;
  }

  .form-grid {
    grid-template-columns: minmax(0, 1.4fr) 180px auto;
  }

  .directory-header {
    grid-template-columns: 1fr auto;
  }
}

@media (max-width: 760px) {
  .users-head,
  .users-row {
    grid-template-columns: 1fr;
  }
}
</style>
