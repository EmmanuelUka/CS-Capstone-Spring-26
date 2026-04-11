<script setup>
import { computed, reactive } from 'vue'

import { useRecruitingStore } from '../store/useRecruitingStore'

const { state, rosterPositions, createArchetype, deleteArchetype } = useRecruitingStore()

const form = reactive({
  name: '',
  position: rosterPositions[0] || 'QB',
  notes: '',
  minimums: [{ statKey: '', minValue: '' }],
})

function humanizeStatKey(key) {
  return key
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (char) => char.toUpperCase())
    .trim()
}

function parseComparableStatValue(value) {
  if (typeof value === 'number') {
    return value
  }

  if (typeof value === 'string') {
    const normalized = Number.parseFloat(value.replace('%', '').trim())
    return Number.isFinite(normalized) ? normalized : null
  }

  return null
}

const positionStatOptions = computed(() => {
  const keys = new Set()

  state.players
    .filter((player) => player.position === form.position)
    .forEach((player) => {
      Object.entries(player.stats || {}).forEach(([key, value]) => {
        if (parseComparableStatValue(value) !== null) {
          keys.add(key)
        }
      })
    })

  return [...keys].sort().map((key) => ({
    value: key,
    label: humanizeStatKey(key),
  }))
})

const enrichedArchetypes = computed(() =>
  state.archetypes.map((archetype) => {
    const matchingPlayers = state.players.filter((player) => {
      if (player.position !== archetype.position) {
        return false
      }

      return archetype.minimums.every((rule) => {
        const playerValue = parseComparableStatValue(player.stats?.[rule.statKey])
        return playerValue !== null && playerValue >= Number(rule.minValue)
      })
    })

    return {
      ...archetype,
      matchingPlayers,
    }
  })
)

function addRule() {
  form.minimums.push({ statKey: '', minValue: '' })
}

function removeRule(index) {
  form.minimums = form.minimums.filter((_, ruleIndex) => ruleIndex !== index)
  if (!form.minimums.length) {
    form.minimums = [{ statKey: '', minValue: '' }]
  }
}

function resetForm() {
  form.name = ''
  form.position = rosterPositions[0] || 'QB'
  form.notes = ''
  form.minimums = [{ statKey: '', minValue: '' }]
}

function submitArchetype() {
  createArchetype({
    name: form.name,
    position: form.position,
    notes: form.notes,
    minimums: form.minimums,
  })

  resetForm()
}

const canSubmit = computed(() =>
  Boolean(
    form.position &&
      form.minimums.some(
        (rule) => rule.statKey && rule.minValue !== '' && Number.isFinite(Number(rule.minValue))
      )
  )
)
</script>

<template>
  <section class="scheme-layout">
    <section class="creator-panel surface-panel">
      <p class="section-label">Scheme Creator</p>
      <h2>Build player archetypes from stat minimums.</h2>
      <p class="panel-copy">
        Create the archetypes your staff uses in the scheme creator, then define the minimum production profile a
        player has to hit to qualify. Example: a running quarterback can require a minimum rushing-yards threshold.
      </p>

      <div class="form-grid">
        <label class="field-group">
          <span>Archetype name</span>
          <input v-model="form.name" type="text" placeholder="Running QB" />
        </label>

        <label class="field-group">
          <span>Position</span>
          <select v-model="form.position">
            <option v-for="position in rosterPositions" :key="position" :value="position">{{ position }}</option>
          </select>
        </label>
      </div>

      <label class="field-group">
        <span>Notes</span>
        <textarea
          v-model="form.notes"
          rows="3"
          placeholder="Describe how this archetype fits the scheme or what coaches are looking for."
        />
      </label>

      <div class="rules-panel">
        <div class="rules-head">
          <div>
            <p class="section-label">Minimum Stat Rules</p>
            <h3>What has to be true?</h3>
          </div>
          <button class="ghost-button" type="button" @click="addRule">Add rule</button>
        </div>

        <div class="rule-list">
          <div v-for="(rule, index) in form.minimums" :key="index" class="rule-row">
            <select v-model="rule.statKey">
              <option value="">Choose stat</option>
              <option v-for="option in positionStatOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>

            <input v-model="rule.minValue" type="number" min="0" step="1" placeholder="Minimum value" />

            <button class="ghost-button" type="button" @click="removeRule(index)">Remove</button>
          </div>
        </div>
      </div>

      <div class="creator-actions">
        <button class="primary-button" type="button" :disabled="!canSubmit" @click="submitArchetype">
          Save archetype
        </button>
      </div>
    </section>

    <section class="library-panel surface-panel">
      <div class="library-head">
        <div>
          <p class="section-label">Archetype Library</p>
          <h3>Saved player profiles</h3>
        </div>
      </div>

      <div v-if="enrichedArchetypes.length" class="archetype-list">
        <article v-for="archetype in enrichedArchetypes" :key="archetype.id" class="archetype-card">
          <div class="archetype-top">
            <div>
              <span class="position-pill">{{ archetype.position }}</span>
              <h4>{{ archetype.name }}</h4>
              <p v-if="archetype.notes">{{ archetype.notes }}</p>
            </div>
            <button class="ghost-button small-button" type="button" @click="deleteArchetype(archetype.id)">
              Delete
            </button>
          </div>

          <div class="rule-chip-list">
            <span v-for="rule in archetype.minimums" :key="`${archetype.id}-${rule.statKey}`" class="rule-chip">
              {{ humanizeStatKey(rule.statKey) }} >= {{ rule.minValue }}
            </span>
          </div>

          <div class="match-panel">
            <strong>{{ archetype.matchingPlayers.length }} matching players</strong>
            <div v-if="archetype.matchingPlayers.length" class="match-list">
              <span v-for="player in archetype.matchingPlayers" :key="player.id" class="match-chip">
                {{ player.name }}
              </span>
            </div>
            <p v-else>No current players hit every minimum for this archetype.</p>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        <strong>No archetypes yet.</strong>
        <p>Create one on the left to start defining scheme-fit player profiles.</p>
      </div>
    </section>
  </section>
</template>

<style scoped>
.scheme-layout,
.rules-panel,
.rule-list,
.archetype-list,
.archetype-card,
.match-panel {
  display: grid;
  gap: 1rem;
}

.creator-panel h2,
.rules-head h3,
.library-head h3 {
  margin: 0.3rem 0 0;
}

.panel-copy,
.archetype-top p,
.match-panel p {
  margin: 0;
  color: var(--text-muted);
}

.form-grid {
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
.field-group textarea,
.rule-row select,
.rule-row input {
  min-height: 3rem;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: var(--bg-soft);
  color: var(--text);
}

.field-group textarea {
  min-height: 6rem;
  resize: vertical;
}

.rules-panel {
  padding: 1rem;
  border-radius: 22px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.03);
}

.rules-head,
.archetype-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}

.rule-row {
  display: grid;
  gap: 0.75rem;
}

.creator-actions {
  display: flex;
  justify-content: flex-start;
}

.archetype-card {
  padding: 1rem;
  border-radius: 22px;
  border: 1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.08), transparent 35%),
    rgba(255, 255, 255, 0.04);
}

.position-pill,
.rule-chip,
.match-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
}

.position-pill {
  margin-bottom: 0.65rem;
  padding: 0.4rem 0.7rem;
  background: rgba(217, 151, 0, 0.16);
  color: var(--accent-strong);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.archetype-top h4 {
  margin: 0;
  font-size: 1.2rem;
}

.small-button {
  min-height: 2.5rem;
}

.rule-chip-list,
.match-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.rule-chip,
.match-chip {
  padding: 0.5rem 0.8rem;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
  font-size: 0.86rem;
}

.match-panel strong {
  color: var(--accent-strong);
}

@media (min-width: 920px) {
  .scheme-layout {
    grid-template-columns: minmax(340px, 0.95fr) minmax(0, 1.05fr);
    align-items: start;
  }

  .form-grid {
    grid-template-columns: minmax(0, 1fr) 180px;
  }

  .rule-row {
    grid-template-columns: minmax(0, 1.2fr) 180px auto;
  }
}
</style>
