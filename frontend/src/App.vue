<template>
  <div class="app-container">
    <div class="card">
      <div class="header">
        <div class="logo">
          <img src="./assets/HashmarkLogoWHITE.svg" alt="Hashmark Logo" />
        </div>
        <div>
          <h1>Hashmark</h1>
          <p>Recruiting Portal</p>
        </div>
      </div>

      <div v-if="loading" class="loading">Loading...</div>

      <div v-else>
        <!-- NOT LOGGED IN -->
        <div v-if="!me" class="login-section">
          <h2>Welcome!</h2>
          <p>Sign in using your Microsoft account.</p>

          <button class="primary-btn" @click="loginMicrosoft">
            Sign in with Microsoft
          </button>
        </div>

        <!-- LOGGED IN -->
        <div v-else class="dashboard">
          <div class="user-info">
            <h2>Welcome, {{ me.name }}</h2>
            <div class="user-meta">
              <span><strong>Email:</strong> {{ me.email }}</span>
              <span><strong>Role:</strong> {{ me.role }}</span>
            </div>

            <button class="secondary-btn" @click="logout">
              Logout
            </button>
          </div>

          <!-- SUPER ADMIN PANEL -->
          <div v-if="me.role === 'SUPER_ADMIN'" class="admin-panel">
            <h3>Invite User</h3>

            <div class="invite-form">
              <input v-model="inviteEmail" placeholder="user@kent.edu" />

              <select v-model="inviteRole">
                <option>ADMIN</option>
                <option>COACH</option>
                <option>SCOUT</option>
              </select>

              <button class="primary-btn" @click="invite">Invite</button>
            </div>

            <p class="status">{{ status }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import axios from "axios";

// Configure API base (dev default)
// Set VITE_API_BASE=http://localhost:5000 in your frontend .env if you want explicit
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

const loading = ref(true);
const me = ref(null);

const inviteEmail = ref("");
const inviteRole = ref("COACH");
const status = ref("");

const csrfToken = ref("");

api.interceptors.request.use((config) => {
  const m = (config.method || "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(m) && csrfToken.value) {
    config.headers["X-CSRF-Token"] = csrfToken.value;
  }
  return config;
});

async function loadCsrf() {
  try {
    const res = await api.get("/api/csrf");
    csrfToken.value = res.data?.csrfToken || "";
  } catch {
    csrfToken.value = "";
  }
}

async function loadMe() {
  loading.value = true;
  const res = await api.get("/api/me");
  me.value = res.data?.email ? res.data : null;
  loading.value = false;
}

function loginMicrosoft() {
  // Redirect to backend login endpoint
  window.location.href = `${API_BASE}/auth/microsoft/login`;
}

async function logout() {
  await api.post("/auth/logout");
  me.value = null;
  await loadCsrf(); // new session after logout
  await loadMe();
}

async function invite() {
  status.value = "Inviting...";
  try {
    await api.post("/api/invite", {
      email: inviteEmail.value,
      role: inviteRole.value,
    });
    status.value = "Invite saved. They can now sign in.";
    inviteEmail.value = "";
  } catch (e) {
    status.value = "Invite failed: " + (e.response?.data?.error || e.message);
  }
}

onMounted(async () => {
  await loadCsrf();
  await loadMe();
});
</script>