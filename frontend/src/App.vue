<script setup>
import { ref, onMounted, computed } from "vue";
import axios from "axios";
import hashmarkLogo from "./assets/HashmarkLogoWHITE.svg";

const API_BASE = "http://localhost:5000";

const loading = ref(true);
const me = ref(null);

// NEW: simple in-app "pages"
const view = ref("home"); // "home" | "account"

const csrfToken = ref("");

const orgs = ref([]);
const selectedOrgId = ref("");

const orgName = ref("");
const adminEmail = ref("");
const seatLimit = ref(25);

const inviteEmail = ref("");
const inviteRole = ref("COACH");

const systemOrgs = ref([]);
const systemOrgMembers = ref(null);

const members = ref([]);

const isSuperAdmin = computed(() => me.value?.systemRole === "SUPER_ADMIN");
const isTeamAdmin = computed(() => me.value?.role === "ADMIN");

const loginError = ref(null);

function goHome() {
  view.value = "home";
}
function goAccount() {
  view.value = "account";
}

async function loadCsrf() {
  const res = await axios.get(`${API_BASE}/api/csrf`, { withCredentials: true });
  csrfToken.value = res.data.csrfToken;
}

async function loadMe() {
  try {
    const res = await axios.get(`${API_BASE}/api/me`, { withCredentials: true });
    me.value = res.data?.email ? res.data : null;

    // NEW: after login, land on Home
    if (me.value) view.value = "home";
    if (!me.value) view.value = "home";
  } finally {
    loading.value = false;
  }
}

async function loadOrgs() {
  const res = await axios.get(`${API_BASE}/api/orgs`, { withCredentials: true });
  orgs.value = res.data.orgs || [];
  selectedOrgId.value = res.data.activeOrgId ? String(res.data.activeOrgId) : "";
}

async function setActiveOrg() {
  if (!selectedOrgId.value) return;
  await axios.post(
    `${API_BASE}/api/set-org`,
    { orgId: Number(selectedOrgId.value) },
    {
      withCredentials: true,
      headers: { "X-CSRF-Token": csrfToken.value },
    }
  );
  await loadMe();
  await loadOrgs();
}

async function inviteMember() {
  await axios.post(
    `${API_BASE}/api/invite`,
    { email: inviteEmail.value, role: inviteRole.value },
    {
      withCredentials: true,
      headers: { "X-CSRF-Token": csrfToken.value },
    }
  );
  inviteEmail.value = "";
  inviteRole.value = "COACH";
  await loadMembers();
}

async function loadMembers() {
  const res = await axios.get(`${API_BASE}/api/members`, { withCredentials: true });
  members.value = res.data.members || [];
}

async function changeMemberRole(userId, newRole) {
  await axios.put(
    `${API_BASE}/api/members/${userId}/role`,
    { role: newRole },
    {
      withCredentials: true,
      headers: { "X-CSRF-Token": csrfToken.value },
    }
  );
  await loadMembers();
}

async function removeMember(userId) {
  await axios.delete(`${API_BASE}/api/members/${userId}`, {
    withCredentials: true,
    headers: { "X-CSRF-Token": csrfToken.value },
  });
  await loadMembers();
}

async function loadSystemOrgs() {
  const res = await axios.get(`${API_BASE}/api/system/orgs`, { withCredentials: true });
  systemOrgs.value = res.data.orgs || [];
}

async function loadSystemOrgMembers(orgId) {
  const res = await axios.get(`${API_BASE}/api/system/orgs/${orgId}/members`, {
    withCredentials: true,
  });
  systemOrgMembers.value = res.data;
}

async function createOrgAndAdmin() {
  await axios.post(
    `${API_BASE}/api/system/create-org-admin`,
    { orgName: orgName.value, adminEmail: adminEmail.value, seatLimit: seatLimit.value },
    {
      withCredentials: true,
      headers: { "X-CSRF-Token": csrfToken.value },
    }
  );
  orgName.value = "";
  adminEmail.value = "";
  seatLimit.value = 25;
  await loadSystemOrgs();
}

async function setTeamAdmin(orgId, email) {
  try {
    await axios.put(
      `${API_BASE}/api/system/orgs/${orgId}/admin`,
      { email }, // backend expects email
      {
        withCredentials: true,
        headers: { "X-CSRF-Token": csrfToken.value },
      }
    );

    status.value = `Team admin changed to ${email}.`;
    await loadSystemOrgMembers(orgId);
    await loadMe();
  } catch (e) {
    const msg = e?.response?.data?.error || e?.message || "set_admin_failed";
    status.value = `Set admin blocked: ${msg}`;
  }
}

async function deleteOrg(orgId) {
  await axios.delete(`${API_BASE}/api/system/orgs/${orgId}`, {
    withCredentials: true,
    headers: { "X-CSRF-Token": csrfToken.value },
  });
  systemOrgMembers.value = null;
  await loadSystemOrgs();
}

async function loginMicrosoft() {
  window.location.href = `${API_BASE}/auth/microsoft/login`;
}

async function logout() {
  await axios.post(
    `${API_BASE}/auth/logout`,
    {},
    {
      withCredentials: true,
      headers: { "X-CSRF-Token": csrfToken.value },
    }
  );
  me.value = null;
  view.value = "home";
  orgs.value = [];
  members.value = [];
  systemOrgs.value = [];
  systemOrgMembers.value = null;
}

onMounted(async () => {
  // 🔴 Check for login error from backend redirect
  const params = new URLSearchParams(window.location.search);
  if (params.get("error") === "invalid_access") {
    loginError.value =
      "Invalid access. No account found or you are not invited to a team.";
    window.history.replaceState({}, document.title, "/");
  }

  await loadCsrf();
  await loadMe();

  if (me.value) {
    await loadOrgs();
    if (isTeamAdmin.value) await loadMembers();
    if (isSuperAdmin.value) await loadSystemOrgs();
  }
});
</script>

<template>
  <div class="app-container">
    <div class="card">
      <!-- Header -->
      <div class="header">
        <div class="logo">
          <img :src="hashmarkLogo" alt="Hashmark Logo" />
        </div>
        <div>
          <h1>Hashmark Recruiting Portal</h1>
          <p>Secure Microsoft-based authentication</p>
        </div>
      </div>

      <div v-if="loading">Loading...</div>

      <!-- NOT LOGGED IN -->
      <div v-else-if="!me" class="login-section">
        <p>You are not logged in.</p>
        <div v-if="loginError" class="error-alert">
          {{ loginError }}
        </div>
        <button class="primary-btn" @click="loginMicrosoft">
          Sign in with Microsoft
        </button>
      </div>

      <!-- LOGGED IN -->
      <div v-else class="dashboard">
        <!-- Simple top bar -->
        <div class="topbar">
          <div class="topbar-left">
            <div class="topbar-title">Hashmark</div>
            <div class="topbar-sub">
              Signed in as <b>{{ me.email }}</b>
            </div>
          </div>

          <div class="topbar-actions">
            <button
              v-if="view !== 'home'"
              class="secondary-btn compact"
              @click="goHome"
            >
              Home
            </button>

            <button
              v-if="view !== 'account'"
              class="secondary-btn compact"
              @click="goAccount"
            >
              View account
            </button>

            <button class="secondary-btn compact" @click="logout">
              Logout
            </button>
          </div>
        </div>

        <!-- LANDING PAGE (HOME) -->
        <div v-if="view === 'home'" class="home">
          <h2>Welcome, {{ me.name }}</h2>
          <p class="muted">
            This is the landing page after login.
          </p>

          <div class="home-grid">
            <div class="home-card">
              <h3>Account</h3>
              <p class="muted">View your profile, teams, and permissions.</p>
              <button class="primary-btn" @click="goAccount">View account</button>
            </div>

            <div class="home-card" v-if="me.orgId">
              <h3>Active Team</h3>
              <p class="muted">
                Team ID: <b>{{ me.orgId }}</b>
                <span v-if="me.role"> • Role: <b>{{ me.role }}</b></span>
              </p>
              <button class="secondary-btn compact" @click="goAccount">
                View Team
              </button>
            </div>
          </div>
        </div>

        <!-- ACCOUNT PAGE (your existing “profile/admin panels”) -->
        <div v-else class="account">
          <div class="user-info">
            <h2>Account</h2>

            <div class="user-meta">
              <span><strong>Name:</strong> {{ me.name }}</span>
              <span><strong>Email:</strong> {{ me.email }}</span>
              <span v-if="me.systemRole"><strong>System Role:</strong> {{ me.systemRole }}</span>
              <span v-if="me.role"><strong>Team Role:</strong> {{ me.role }}</span>
              <span v-else class="warn"><strong>Team:</strong> No team selected</span>
            </div>
          </div>

          <!-- Org picker (if multi-org) -->
          <div v-if="orgs.length > 0" class="admin-panel">
            <h3>Teams</h3>
            <p class="muted">Select which team you are actively working in.</p>

            <div class="invite-form">
              <select v-model="selectedOrgId">
                <option value="">-- Select team --</option>
                <option v-for="o in orgs" :key="o.id" :value="String(o.id)">
                  {{ o.name }} ({{ o.role }})
                </option>
              </select>

              <button class="secondary-btn compact" @click="setActiveOrg" :disabled="!selectedOrgId">
                Set active team
              </button>
            </div>
          </div>

          <!-- Team Admin -->
          <div v-if="isTeamAdmin && me.orgId" class="admin-panel">
            <h3>Team Admin Panel</h3>

            <h4>Invite a member</h4>
            <div class="invite-form">
              <input v-model="inviteEmail" placeholder="email@domain.com" />
              <select v-model="inviteRole">
                <option value="COACH">COACH</option>
                <option value="SCOUT">SCOUT</option>
              </select>
              <button class="primary-btn" @click="inviteMember" :disabled="!inviteEmail">
                Invite
              </button>
            </div>

            <h4 style="margin-top: 16px;">Members</h4>
            <div class="members" v-if="members.length">
              <div class="member-row" v-for="m in members" :key="m.user_id">
                <div>
                  <b>{{ m.email }}</b>
                  <div class="muted">Role: {{ m.role }}</div>
                </div>

                <div class="invite-form" style="justify-content: flex-end;">

                  <!-- Your own row -->
                  <template v-if="m.user_id === me.userId">
                    <span class="pill">You</span>
                  </template>

                  <!-- Team admin row (ADMIN) -->
                  <template v-else-if="(m.role || '').toUpperCase() === 'ADMIN'">
                    <span class="pill">TEAM ADMIN</span>
                  </template>

                  <!-- Normal members: allow change role + remove -->
                  <template v-else>
                    <select :value="m.role" @change="e => changeMemberRole(m.user_id, e.target.value)">
                      <option value="COACH">COACH</option>
                      <option value="SCOUT">SCOUT</option>
                    </select>

                    <button class="secondary-btn compact danger-btn" @click="removeMember(m.user_id)">
                      Remove
                    </button>
                  </template>

                </div>
              </div>
            </div>
            <p v-else class="muted">No members loaded yet.</p>
          </div>

          <!-- System SUPER_ADMIN -->
          <div v-if="isSuperAdmin" class="admin-panel">
            <h3>System Admin Panel</h3>

            <h4>Create org + set team admin</h4>
            <div class="invite-form">
              <input v-model="orgName" placeholder="Organization name" />
              <input v-model="adminEmail" placeholder="admin@email.com" />
              <input v-model.number="seatLimit" type="number" min="1" placeholder="Seat limit" />
              <button class="primary-btn" @click="createOrgAndAdmin" :disabled="!orgName || !adminEmail">
                Create
              </button>
            </div>

            <h4 style="margin-top: 16px;">Organizations</h4>
            <div class="members" v-if="systemOrgs.length">
              <div class="member-row" v-for="o in systemOrgs" :key="o.id">
                <div>
                  <b>{{ o.name }}</b>
                  <div class="muted">Seats: {{ o.seat_limit }}</div>
                </div>

                <div class="invite-form" style="justify-content: flex-end;">
                  <button class="secondary-btn compact" @click="loadSystemOrgMembers(o.id)">
                    View members
                  </button>
                  <button class="secondary-btn compact danger-btn" @click="deleteOrg(o.id)">
                    Delete org
                  </button>
                </div>
              </div>
            </div>

            <div v-if="systemOrgMembers" class="admin-panel">
              <h4>Org Members: {{ systemOrgMembers.org?.name }}</h4>
              <p class="muted">
                Seats used: {{ systemOrgMembers.seatsUsed }} / {{ systemOrgMembers.org?.seat_limit }}
              </p>

              <div class="members" v-if="systemOrgMembers.members?.length">
                <div class="member-row" v-for="m in systemOrgMembers.members" :key="m.user_id">
                  <div>
                    <b>{{ m.email }}</b>
                    <div class="muted">Role: {{ m.role }}</div>
                  </div>

                  <div class="invite-form" style="justify-content: flex-end;">
                    <button
                      v-if="(m.role || '').toUpperCase() !== 'ADMIN'"
                      class="secondary-btn compact"
                      @click="setTeamAdmin(systemOrgMembers.org.id, m.email)"
                    >
                      Set as TEAM ADMIN
                    </button>
                    <span v-else class="pill">Current TEAM ADMIN</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- No org access -->
          <div v-if="!me.orgId && !isSuperAdmin" class="admin-panel">
            <h3>Access pending</h3>
            <p>
              You're signed in, but you don't have access to a team yet.
              Ask your team admin to invite you.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>