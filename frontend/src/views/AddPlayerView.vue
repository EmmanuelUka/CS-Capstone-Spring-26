<script setup>
import { computed, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'

import { POSITION_STATS } from '../data/positionStats'
import { useRecruitingStore } from '../store/useRecruitingStore'

const router = useRouter()
const { rosterPositions } = useRecruitingStore()
const typeOptions = computed(() => ['High School', 'Transfer'])

const form = reactive({
  name: '',
  position: rosterPositions[0] || 'QB',
  school: '',
  city: '',
  state: '',
  classYear: new Date().getFullYear() + 1,
  height: '',
  weight: '',
  type: typeOptions.value[0],
  summary: '',
  stats: {},
})

const statsForPosition = computed(() => POSITION_STATS[form.position] || [])

watch(
  () => form.position,
  (position) => {
    for (const statKey of POSITION_STATS[position] || []) {
      if (!(statKey in form.stats)) {
        form.stats[statKey] = ''
      }
    }
  },
  { immediate: true }
)

function formatStatLabel(statKey) {
  return statKey
    .replace(/^stat_/, '')
    .split('_')
    .map((part) => (part === part.toUpperCase() ? part : `${part.charAt(0).toUpperCase()}${part.slice(1)}`))
    .join(' ')
}
</script>

<template>
  <section class="add-player-layout">
    <section class="hero-panel surface-panel">
      <div class="hero-head">
        <div>
          <p class="eyebrow section-label">Add Player</p>
          <h2>Create a new prospect profile.</h2>
          <p>Use this page to capture the base player record before wiring the real save flow.</p>
        </div>
        <button class="ghost-button" type="button" @click="router.push('/players')">Back to board</button>
      </div>
    </section>

    <section class="form-panel surface-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow section-label">Player Intake</p>
          <h3>Core player information</h3>
        </div>
      </div>

      <div class="form-grid">
        <label class="field-group field-span-2">
          <span>Player Name</span>
          <input v-model="form.name" type="text" placeholder="Evan Brooks" />
        </label>

        <label class="field-group">
          <span>Position</span>
          <select v-model="form.position">
            <option v-for="position in rosterPositions" :key="position" :value="position">{{ position }}</option>
          </select>
        </label>

        <label class="field-group">
          <span>Type</span>
          <select v-model="form.type">
            <option v-for="type in typeOptions" :key="type" :value="type">{{ type }}</option>
          </select>
        </label>

        <label class="field-group">
          <span>School</span>
          <input v-model="form.school" type="text" placeholder="St. Xavier" />
        </label>

        <label class="field-group">
          <span>City</span>
          <input v-model="form.city" type="text" placeholder="Cincinnati" />
        </label>

        <label class="field-group">
          <span>State</span>
          <input v-model="form.state" type="text" maxlength="2" placeholder="OH" />
        </label>

        <label class="field-group">
          <span>Class Year</span>
          <input v-model="form.classYear" type="number" min="2024" step="1" />
        </label>

        <label class="field-group">
          <span>Height</span>
          <input v-model="form.height" type="text" placeholder="6'2&quot;" />
        </label>

        <label class="field-group">
          <span>Weight</span>
          <input v-model="form.weight" type="number" min="0" step="1" placeholder="204" />
        </label>

        <label class="field-group field-span-2">
          <span>Summary</span>
          <textarea
            v-model="form.summary"
            rows="4"
            placeholder="Add the short recruiting summary that should appear on the player card."
          />
        </label>
      </div>

      <div class="stats-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow section-label">Position Stats</p>
            <h3>{{ form.position }} stat inputs</h3>
          </div>
        </div>

        <div v-if="statsForPosition.length" class="stat-grid">
          <label v-for="statKey in statsForPosition" :key="statKey" class="field-group">
            <span>{{ formatStatLabel(statKey) }}</span>
            <input v-model="form.stats[statKey]" type="number" step="any" placeholder="Enter value" />
          </label>
        </div>

        <p v-else class="stats-empty">
          No position-specific stat fields are configured for {{ form.position }}.
        </p>
      </div>
    </section>

    <section class="notes-panel surface-panel">
      <p class="eyebrow section-label">Next Step</p>
      <h3>Save behavior is not wired yet.</h3>
      <p>
        This page is in place for navigation and layout. The actual create-player action still needs to be connected to
        the store or backend API.
      </p>
    </section>
  </section>
</template>

<style scoped>
.add-player-layout,
.form-panel,
.stats-panel {
  display: grid;
  gap: 1rem;
}

.hero-head,
.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}

.hero-panel h2,
.panel-head h3,
.notes-panel h3 {
  margin: 0.3rem 0 0;
}

.hero-panel p:last-child,
.notes-panel > p:last-child {
  margin: 0.35rem 0 0;
  color: var(--text-muted);
}

.form-grid {
  display: grid;
  gap: 0.85rem;
}

.stat-grid {
  display: grid;
  gap: 0.85rem;
}

.field-group {
  display: grid;
  gap: 0.45rem;
}

.field-group span {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-subtle);
}

.field-group input,
.field-group select,
.field-group textarea {
  min-height: 3rem;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: var(--bg-soft);
  color: var(--text);
}

.field-group select {
  appearance: none;
  color-scheme: dark;
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.08), rgba(255, 255, 255, 0.02)),
    var(--bg-soft);
}

.field-group select option {
  background: #102445;
  color: #f4f7ff;
}

.field-group textarea {
  min-height: 7rem;
  resize: vertical;
}

.stats-panel {
  padding: 1rem;
  border-radius: 22px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.03);
}

.stats-empty {
  margin: 0;
  color: var(--text-muted);
}

@media (min-width: 900px) {
  .form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .field-span-2 {
    grid-column: 1 / -1;
  }
}
</style>
