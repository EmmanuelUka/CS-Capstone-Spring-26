<script setup>
import { computed, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'

import { POSITION_STATS } from '../data/positionStats'
import { useRecruitingStore } from '../store/useRecruitingStore'

const router = useRouter()
const { rosterPositions } = useRecruitingStore()

const typeOptions = ['High School', 'Transfer']

const stateOptions = [
  'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
]

const currentYear = new Date().getFullYear()

const form = reactive({
  name: '',
  position: rosterPositions[0] || 'QB',
  school: '',
  city: '',
  state: '',
  classYear: currentYear + 1,
  heightFeet: '',
  heightInches: '',
  weight: '',
  type: typeOptions[0],
  summary: '',
  stats: {},
})

const statsForPosition = computed(() => POSITION_STATS[form.position] || [])

watch(
  () => form.position,
  (position) => {
    const nextStats = {}
    for (const statKey of POSITION_STATS[position] || []) {
      nextStats[statKey] = form.stats[statKey] ?? ''
    }
    form.stats = nextStats
  },
  { immediate: true }
)

watch(
  () => form.heightFeet,
  (value) => {
    if (value === '') return
    const numeric = Number(value)
    if (Number.isNaN(numeric)) {
      form.heightFeet = ''
      return
    }
    if (numeric < 0) form.heightFeet = 0
    if (numeric > 8) form.heightFeet = 8
  }
)

watch(
  () => form.heightInches,
  (value) => {
    if (value === '') return
    const numeric = Number(value)
    if (Number.isNaN(numeric)) {
      form.heightInches = ''
      return
    }
    if (numeric < 0) form.heightInches = 0
    if (numeric > 11) form.heightInches = 11
  }
)

function formatStatLabel(statKey) {
  return statKey
    .replace(/^stat_/, '')
    .split('_')
    .map((part) => (part === part.toUpperCase() ? part : `${part.charAt(0).toUpperCase()}${part.slice(1)}`))
    .join(' ')
}

const builtHeight = computed(() => {
  if (form.heightFeet === '' || form.heightInches === '') return ''
  return `${form.heightFeet}'${form.heightInches}"`
})

const isFormValid = computed(() => {
  return (
    form.name.trim() &&
    form.position &&
    form.type &&
    form.state &&
    form.classYear &&
    form.heightFeet !== '' &&
    form.heightInches !== '' &&
    Number(form.heightInches) >= 0 &&
    Number(form.heightInches) <= 11 &&
    form.weight !== '' &&
    Number(form.weight) > 0
  )
})

async function submitPlayer() {
  if (!isFormValid.value) return

  const payload = {
    name: form.name.trim(),
    position: form.position,
    school: form.school.trim(),
    city: form.city.trim(),
    state: form.state,
    classYear: Number(form.classYear),
    height: builtHeight.value,
    weight: Number(form.weight),
    type: form.type,
    summary: form.summary.trim(),
    stats: form.stats,
  }

  try {
    const csrfRes = await fetch('/api/csrf', {
      credentials: 'include',
    })
    const { csrfToken } = await csrfRes.json()

    const res = await fetch('/api/create_player', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`HTTP ${res.status}: ${text}`)
    }

    const data = await res.json()
    console.log('Created player:', data)
    router.push('/players')
  } catch (err) {
    console.error('Error creating player:', err.message)
  }
}
</script>

<template>
  <section class="add-player-layout">
    <section class="hero-panel surface-panel">
      <div class="hero-head">
        <div>
          <p class="eyebrow section-label">Add Player</p>
          <h2>Create a new prospect profile.</h2>
          <p>Fill out the required fields to save a new player record.</p>
        </div>
        <button class="ghost-button" type="button" @click="router.push('/players')">
          Back to board
        </button>
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
          <span>Player Name <em>*</em></span>
          <input
            v-model="form.name"
            type="text"
            placeholder="Evan Brooks"
            required
          />
        </label>

        <label class="field-group">
          <span>Position <em>*</em></span>
          <select v-model="form.position" required>
            <option
              v-for="position in rosterPositions"
              :key="position"
              :value="position"
            >
              {{ position }}
            </option>
          </select>
        </label>

        <label class="field-group">
          <span>Type <em>*</em></span>
          <select v-model="form.type" required>
            <option
              v-for="type in typeOptions"
              :key="type"
              :value="type"
            >
              {{ type }}
            </option>
          </select>
        </label>

        <label class="field-group">
          <span>School</span>
          <input
            v-model="form.school"
            type="text"
            placeholder="St. Xavier"
          />
        </label>

        <label class="field-group">
          <span>City</span>
          <input
            v-model="form.city"
            type="text"
            placeholder="Cincinnati"
          />
        </label>

        <label class="field-group">
          <span>State <em>*</em></span>
          <select v-model="form.state" required>
            <option disabled value="">Select state</option>
            <option
              v-for="state in stateOptions"
              :key="state"
              :value="state"
            >
              {{ state }}
            </option>
          </select>
        </label>

        <label class="field-group">
          <span>Class Year <em>*</em></span>
          <input
            v-model="form.classYear"
            type="number"
            :min="currentYear"
            step="1"
            required
          />
        </label>

        <div class="field-group">
          <span>Height <em>*</em></span>
          <div class="height-inputs">
            <input
              v-model="form.heightFeet"
              type="number"
              min="0"
              max="8"
              step="1"
              placeholder="6"
              required
            />
            <span class="height-mark">'</span>
            <input
              v-model="form.heightInches"
              type="number"
              min="0"
              max="11"
              step="1"
              placeholder="2"
              required
            />
            <span class="height-mark">"</span>
          </div>
          <small v-if="builtHeight" class="helper-text">Saved as {{ builtHeight }}</small>
        </div>

        <div class="field-group">
          <span>Weight <em>*</em></span>
          <div class="weight-input">
            <input
              v-model="form.weight"
              type="number"
              min="1"
              step="1"
              placeholder="204"
              required
            />
            <span class="unit-label">lbs</span>
          </div>
        </div>

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
          <label
            v-for="statKey in statsForPosition"
            :key="statKey"
            class="field-group"
          >
            <span>{{ formatStatLabel(statKey) }}</span>
            <input
              v-model="form.stats[statKey]"
              type="number"
              step="any"
              placeholder="Enter value"
            />
          </label>
        </div>

        <p v-else class="stats-empty">
          No position-specific stat fields are configured for {{ form.position }}.
        </p>
      </div>

      <div class="form-actions">
        <p class="required-note"><em>*</em> Required fields</p>
        <button
          class="save-button"
          type="button"
          :disabled="!isFormValid"
          @click="submitPlayer"
        >
          Save Player
        </button>
      </div>
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
.panel-head h3 {
  margin: 0.3rem 0 0;
}

.hero-panel p:last-child {
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

.field-group span em,
.required-note em {
  font-style: normal;
  color: #ff8a8a;
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
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.field-group input:focus,
.field-group select:focus,
.field-group textarea:focus {
  outline: none;
  border-color: rgba(255, 183, 94, 0.8);
  box-shadow: 0 0 0 4px rgba(255, 183, 94, 0.12);
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

.height-inputs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto;
  gap: 0.5rem;
  align-items: center;
}

.height-inputs input {
  text-align: center;
}

.height-mark {
  font-size: 1rem;
  font-weight: 800;
  color: var(--text-muted);
}

.weight-input {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.6rem;
  align-items: center;
}

.unit-label {
  font-size: 0.9rem;
  font-weight: 800;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.helper-text {
  font-size: 0.82rem;
  color: var(--text-muted);
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

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.required-note {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-muted);
}

.save-button {
  min-width: 11rem;
  min-height: 3.25rem;
  padding: 0.9rem 1.4rem;
  border: 0;
  border-radius: 18px;
  font-weight: 800;
  font-size: 0.95rem;
  letter-spacing: 0.04em;
  cursor: pointer;
  color: #08111f;
  background: linear-gradient(135deg, #ffb75e 0%, #ffd9a0 100%);
  box-shadow: 0 14px 30px rgba(255, 183, 94, 0.2);
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}

.save-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(255, 183, 94, 0.28);
}

.save-button:active:not(:disabled) {
  transform: translateY(0);
}

.save-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  box-shadow: none;
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