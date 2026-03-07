<template>
  <div class="app-container">
    <div class="card">
      <!-- Top header/logo area -->
      <div class="header">
        <div class="logo">
          <img src="./assets/HashmarkLogoWHITE.svg" alt="Hashmark Logo" />
        </div>
        <div>
          <h1>Hashmark</h1>
          <p>Recruiting Assistant</p>
        </div>
      </div>

      <!-- Initial loading state while checking session/user -->
      <div v-if="loading" class="loading">Loading...</div>

      <div v-else>
        <!-- If no user is logged in, show login screen -->
        <div v-if="!me" class="login-section">
          <h2>Welcome!</h2>
          <p>Sign in using your Microsoft account.</p>

          <button class="btn primary-btn" @click="loginMicrosoft">
            Sign in with Microsoft
          </button>

          <!-- General status message for login-related feedback -->
          <p v-if="status" class="status">{{ status }}</p>
        </div>

        <!-- If user is logged in, show dashboard -->
        <div v-else class="dashboard">
          <div class="user-info">
            <h2>Welcome, {{ me.name }}</h2>

            <!-- Basic logged-in user info -->
            <div class="user-meta">
              <span><strong>Email:</strong> {{ me.email }}</span>
              <span><strong>Role:</strong> {{ me.role }}</span>
            </div>

            <!-- User-level actions -->
            <div class="user-actions">
              <button class="btn secondary-btn" @click="refresh">Refresh</button>
              <button class="btn secondary-btn danger-btn" @click="logout">
                Logout
              </button>
            </div>
          </div>

          <!-- Admin/Super Admin only: Add User panel -->
          <div v-if="isAdminOrSuper" class="admin-panel">
            <h3>Add User</h3>
            <p class="hint">Adds a new user</p>

            <div class="user-form">
              <input v-model="addEmail" placeholder="user@kent.edu" />

              <!-- Only SUPER_ADMIN can create ADMIN accounts -->
              <select v-model="addRole">
                <option value="COACH">COACH</option>
                <option v-if="isSuperAdmin" value="ADMIN">ADMIN</option>
              </select>

              <button class="btn primary-btn" @click="addUser">Add</button>
            </div>

            <p class="status">{{ addStatus }}</p>
          </div>

          <!-- Admin/Super Admin only: User directory -->
          <div v-if="isAdminOrSuper" class="admin-panel">
            <h3>User Directory</h3>

            <div v-if="usersLoading" class="loading">Loading users...</div>

            <div v-else class="users-table">
              <div class="users-head">
                <span>Email</span>
                <span>Role</span>
                <span>Actions</span>
              </div>

              <div v-for="u in users" :key="u.email" class="users-row">
                <span class="mono">{{ u.email }}</span>
                <span>{{ u.role }}</span>

                <span class="row-actions">
                  <button
                    v-if="isAdmin && canAdminToggle(u)"
                    class="btn secondary-btn small danger-btn"
                    @click="deleteUserAccount(u)"
                  >
                    Delete
                  </button>

                  <button
                    v-if="isSuperAdmin && canSuperToggle(u)"
                    class="btn secondary-btn small danger-btn"
                    @click="deleteUserAccount(u)"
                  >
                    Delete
                  </button>

                  <button
                    v-if="isSuperAdmin && canPromoteToAdmin(u)"
                    class="btn secondary-btn small"
                    @click="setRole(u.email, 'ADMIN')"
                  >
                    Promote to ADMIN
                  </button>

                  <button
                    v-if="isSuperAdmin && canDemoteAdmin(u)"
                    class="btn secondary-btn small"
                    @click="setRole(u.email, 'COACH')"
                  >
                    Demote ADMIN
                  </button>
                </span>
              </div>
            </div>

            <p class="status">{{ usersStatus }}</p>
          </div>

          <p v-if="status" class="status">{{ status }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "./api";

// =========================================================
// Config / API
// =========================================================

// Backend base URL from Vite env, fallback to local Flask dev server
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

// =========================================================
// Reactive State
// =========================================================

// Main loading state while app checks current login/session
const loading = ref(true);

// General-purpose status text shown in UI
const status = ref("");

// Holds the current logged-in user object from /api/me
const me = ref(null);

// Stores current CSRF token used for protected write requests
const csrfToken = ref("");

// Add user form state
const addEmail = ref("");
const addRole = ref("COACH");
const addStatus = ref("");

// user directory state
const users = ref([]);
const usersLoading = ref(false);
const usersStatus = ref("");

// =========================================================
// Computed Role Helpers
// =========================================================

const isSuperAdmin = computed(() => me.value?.role === "SUPER_ADMIN");
const isAdmin = computed(() => me.value?.role === "ADMIN");
const isAdminOrSuper = computed(() => isAdmin.value || isSuperAdmin.value);

// =========================================================
// Axios Request Hook
// =========================================================

// Automatically attach CSRF token to any state-changing request
api.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();

  if (["post", "put", "patch", "delete"].includes(method) && csrfToken.value) {
    config.headers["X-CSRF-Token"] = csrfToken.value;
  }

  return config;
});

// =========================================================
// Utility Helpers
// =========================================================

// Reads auth_error from the URL after backend redirect
// and turns it into a user-friendly message.
function consumeAuthErrorFromUrl() {
  const params = new URLSearchParams(window.location.search);

  const code = params.get("auth_error");
  const auth = params.get("auth");

  const messages = {
    invalid_state: "Login failed (invalid session state). Please try again.",
    missing_code: "Login failed (missing authorization code). Please try again.",
    token_failed: "Login failed while signing in. Please try again.",
    graph_timeout: "Microsoft took too long to respond. Please try again.",
    graph_failed: "Login failed while contacting Microsoft. Please try again.",
    domain_not_allowed: "Access denied: your email domain is not allowed.",
    access_not_granted: "Access not granted. Contact your administrator.",
  };

  // Handle normal auth_error codes
  if (code) {
    if (!messages[code]) {
      console.warn("Unknown auth_error received from backend:", code);
    }

    status.value = messages[code] || "Login failed. Please try again.";
    params.delete("auth_error");
  }

  // Handle ?auth=denied case
  else if (auth === "denied") {
    status.value = "Access denied. Contact your administrator.";
    params.delete("auth");
  }

  if (!code && auth !== "denied") return;

  const newQuery = params.toString();
  const newUrl =
    window.location.pathname +
    (newQuery ? `?${newQuery}` : "") +
    window.location.hash;

  window.history.replaceState({}, "", newUrl);
}

function isSelf(user) {
  return (user.email || "").toLowerCase() === (me.value?.email || "").toLowerCase();
}

// =========================================================
// Auth / Session Loaders
// =========================================================

// Loads CSRF token from backend
async function loadCsrf() {
  try {
    const res = await api.get("/api/csrf");
    csrfToken.value = res.data?.csrfToken || "";
  } catch {
    csrfToken.value = "";
  }
}

// Loads current session user from backend
async function loadMe() {
  loading.value = true;

  try {
    const res = await api.get("/api/me");
    me.value = res.data?.email ? res.data : null;
  } catch {
    me.value = null;
  } finally {
    loading.value = false;
  }
}

// Loads all users for the user directory.
// Only runs if current user is ADMIN or SUPER_ADMIN.
async function loadUsers() {
  if (!isAdminOrSuper.value) return;

  usersLoading.value = true;
  usersStatus.value = "";

  try {
    const res = await api.get("/api/users");
    users.value = (res.data?.users || []).map((user) => ({ ...user }));
  } catch (e) {
    usersStatus.value =
      "Failed to load users: " + (e.response?.data?.error || e.message);
  } finally {
    usersLoading.value = false;
  }
}

// =========================================================
// Auth Actions
// =========================================================

// Sends browser to backend Microsoft login route
function loginMicrosoft() {
  window.location.href = `${API_BASE}/auth/microsoft/login`;
}

// Logs user out, clears local state, then reloads fresh session/csrf state
async function logout() {
  await api.post("/auth/logout");
  me.value = null;
  users.value = [];

  await loadCsrf();
  await loadMe();
}

// Refreshes the app state manually
async function refresh() {
  status.value = "";
  addStatus.value = "";
  usersStatus.value = "";

  await loadCsrf();
  await loadMe();
  await loadUsers();
}

// =========================================================
// Admin Actions
// =========================================================

// Adds a new user through backend admin route
async function addUser() {
  addStatus.value = "Adding...";

  try {
    const res = await api.post("/api/users", {
      email: addEmail.value,
      role: addRole.value,
    });

    const resultStatus = res?.data?.status;

    if (resultStatus === "user_exists") {
      addStatus.value = "That user already exists. No changes were made.";
    } else if (resultStatus === "created") {
      addStatus.value = "Added. They can now sign in.";
      addEmail.value = "";
    } else {
      addStatus.value = "Done.";
      addEmail.value = "";
    }

    await loadUsers();
  } catch (e) {
    const err = e.response?.data?.error || e.message;
    addStatus.value = "Add failed: " + err;
  }
}

// Deletes a user account
async function deleteUserAccount(user) {
  usersStatus.value = "";

  try {
    await api.delete("/api/users", {
      data: { email: user.email },
    });
    await loadUsers();
  } catch (e) {
    usersStatus.value =
      "Delete failed: " + (e.response?.data?.error || e.message);
  }
}

// Updates a user's role
async function setRole(email, role) {
  usersStatus.value = "";

  try {
    await api.patch("/api/users/role", { email, role });
    await loadUsers();
  } catch (e) {
    usersStatus.value =
      "Role update failed: " + (e.response?.data?.error || e.message);
  }
}

// =========================================================
// Permission Helpers
// =========================================================

// ADMIN can only delete COACH users, and never themselves
function canAdminToggle(user) {
  if (isSelf(user)) return false;
  const role = (user.role || "").toUpperCase();
  return role === "COACH";
}

// SUPER_ADMIN can delete anyone except another SUPER_ADMIN and self
function canSuperToggle(user) {
  if (isSelf(user)) return false;
  const role = (user.role || "").toUpperCase();
  return role !== "SUPER_ADMIN";
}

// SUPER_ADMIN can promote COACH to ADMIN
function canPromoteToAdmin(user) {
  if (isSelf(user)) return false;
  const role = (user.role || "").toUpperCase();
  return role === "COACH";
}

// SUPER_ADMIN can demote ADMIN to COACH
function canDemoteAdmin(user) {
  if (isSelf(user)) return false;
  const role = (user.role || "").toUpperCase();
  return role === "ADMIN";
}

// =========================================================
// Lifecycle
// =========================================================

// On first mount, load auth error (if any), csrf, current user, and user list
onMounted(async () => {
  consumeAuthErrorFromUrl();
  await loadCsrf();
  await loadMe();
  await loadUsers();
});
</script>