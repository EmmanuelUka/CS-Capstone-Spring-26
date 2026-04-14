<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import SearchableDropdown from '../components/SearchableDropdown.vue'
import { useRecruitingStore } from '../store/useRecruitingStore'

const router = useRouter()
const {
  state,
  createShortlist,
  deleteShortlist,
  addPlayerToShortlist,
  removePlayerFromShortlist,
  addPositionSlot,
  removePositionSlot,
  rosterPositions,
  getPlayerById,
} = useRecruitingStore()

const form = ref({
  name: '',
  color: '#ffb75e',
  positions: ['QB', 'WR'],
})
const newSlotPosition = ref(rosterPositions[0] || '')
const listSlotSelection = ref(rosterPositions[0] || '')

const positionOptions = computed(() =>
  rosterPositions.map((position) => ({
    value: position,
    label: position,
    description: 'Position slot',
  }))
)

const groups = computed(() =>
  state.shortlists.map((list) => ({
    ...list,
    filledSlots: list.slots.filter((slot) => slot.playerId),
    slots: list.slots.map((slot) => ({
      ...slot,
      player: slot.playerId ? getPlayerById(slot.playerId) : null,
      options: state.players
        .filter((candidate) => candidate.position === slot.position)
        .map((candidate) => ({
          value: candidate.id,
          label: candidate.name,
          description: `${candidate.school} - Rating ${candidate.rating}`,
        })),
    })),
  }))
)

function submitShortlist() {
  createShortlist(form.value)
  form.value = { name: '', color: '#ffb75e', positions: ['QB', 'WR'] }
  listSlotSelection.value = rosterPositions[0] || ''
}

function addDraftSlot() {
  if (!listSlotSelection.value) {
    return
  }

  form.value.positions = [...form.value.positions, listSlotSelection.value]
}

function removeDraftSlot(index) {
  form.value.positions = form.value.positions.filter((_, slotIndex) => slotIndex !== index)
}

function addSlotToList(shortlistId) {
  if (!newSlotPosition.value) {
    return
  }

  addPositionSlot(shortlistId, newSlotPosition.value)
}
</script>

<template>
  <section class="shortlists-layout">
    <section class="hero-panel surface-panel">
      <p class="eyebrow section-label">Shortlists</p>
      <h2>Build position-based roster lists.</h2>
      <p>Pick the positions you want in the list first, then fill those slots with players.</p>
    </section>

    <section class="group-panel surface-panel">
      <div class="panel-header">
        <div>
          <p class="eyebrow section-label">Create Group</p>
          <h3>New shortlist</h3>
        </div>
      </div>

      <div class="create-grid">
        <input v-model="form.name" type="text" placeholder="Priority Board">
        <input v-model="form.color" type="color">
        <button class="primary-button" type="button" :disabled="!form.positions.length" @click="submitShortlist">
          Create
        </button>
      </div>

      <div class="position-picker">
        <p class="picker-label">Build the slot list coaches want to fill</p>
        <div class="slot-builder">
          <SearchableDropdown
            v-model="listSlotSelection"
            :options="positionOptions"
            placeholder="Choose a position"
            search-placeholder="Search positions"
            empty-label="No positions matched."
          />
          <button class="ghost-button" type="button" @click="addDraftSlot">Add slot</button>
        </div>
        <div v-if="form.positions.length" class="draft-slot-list">
          <div
            v-for="(position, index) in form.positions"
            :key="`${position}-${index}`"
            class="draft-slot-chip"
          >
            <span>{{ index + 1 }}. {{ position }}</span>
            <button type="button" @click="removeDraftSlot(index)">Remove</button>
          </div>
        </div>
        <p v-if="!form.positions.length" class="picker-label">Select at least one position to create the list.</p>
      </div>
    </section>

    <section v-if="groups.length" class="group-stack">
      <section v-for="group in groups" :key="group.id" class="group-panel surface-panel">
        <div class="group-header">
          <div>
            <span class="swatch" :style="{ background: group.color }" />
            <h3>{{ group.name }}</h3>
            <p>{{ group.filledSlots.length }} of {{ group.slots.length }} positions filled</p>
          </div>

          <button class="ghost-button" type="button" @click="deleteShortlist(group.id)">Delete Group</button>
        </div>

        <div class="slot-builder">
          <SearchableDropdown
            v-model="newSlotPosition"
            :options="positionOptions"
            placeholder="Choose a position"
            search-placeholder="Search positions"
            empty-label="No positions matched."
          />
          <button class="ghost-button" type="button" @click="addSlotToList(group.id)">Add slot</button>
        </div>

        <div class="position-grid">
          <div v-for="slot in group.slots" :key="slot.id" class="position-card">
            <div class="position-card-head">
              <strong>{{ slot.position }}</strong>
              <div class="slot-head-actions">
                <span v-if="slot.player">{{ slot.player.rating }}</span>
                <button class="slot-remove-button" type="button" @click="removePositionSlot(group.id, slot.id)">
                  Remove slot
                </button>
              </div>
            </div>

            <SearchableDropdown
              :model-value="slot.playerId"
              :options="[
                {
                  value: null,
                  label: slot.player ? `Clear ${slot.player.name}` : `Assign ${slot.position}`,
                  description: slot.player ? 'Remove current assignment' : 'No player assigned yet',
                },
                ...slot.options,
              ]"
              :placeholder="slot.player ? slot.player.name : `Assign ${slot.position}`"
              search-placeholder="Search players"
              empty-label="No players matched."
              @update:model-value="addPlayerToShortlist(group.id, slot.position, $event)"
            />
          </div>
        </div>
      </section>
    </section>

    <section v-else class="group-panel surface-panel empty-state">
      <strong>No shortlist groups yet.</strong>
      <p>Create one above to start organizing players by position.</p>
    </section>
  </section>
</template>

<style scoped>
.shortlists-layout,
.group-stack {
  display: grid;
  gap: 1rem;
}

.group-panel,
.position-card {
  position: relative;
  z-index: 0;
}

.group-panel:has(.searchable-dropdown.open),
.position-card:has(.searchable-dropdown.open) {
  z-index: 90;
}

.hero-panel h2,
.group-header h3 {
  margin: 0.3rem 0 0;
}

.hero-panel p:last-child,
.group-header p,
.empty-state p,
.picker-label {
  margin: 0.35rem 0 0;
  color: rgba(242, 236, 227, 0.72);
}

.panel-header,
.group-header,
.position-card-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.create-grid,
.position-grid {
  display: grid;
  gap: 0.75rem;
}

.position-picker,
.draft-slot-list {
  display: grid;
  gap: 0.75rem;
}

.create-grid input {
  min-height: 3rem;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: #f2ece3;
}

.create-grid input[type='color'] {
  padding: 0.3rem;
}

.picker-label {
  font-size: 0.86rem;
}

.slot-builder {
  display: grid;
  gap: 0.75rem;
  min-width: 0;
}

.slot-builder :deep(.searchable-dropdown),
.position-card :deep(.searchable-dropdown) {
  min-width: 0;
}

.slot-builder :deep(.dropdown-trigger),
.position-card :deep(.dropdown-trigger) {
  min-height: 3rem;
}

.slot-builder :deep(.dropdown-panel),
.position-card :deep(.dropdown-panel) {
  min-width: 100%;
}

.draft-slot-list {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.draft-slot-chip {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
  min-height: 2.75rem;
  padding: 0.75rem 0.9rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
}

.draft-slot-chip span,
.draft-slot-chip button,
.slot-remove-button {
  color: #f8f2e8;
}

.draft-slot-chip span {
  font-weight: 800;
}

.draft-slot-chip button,
.slot-remove-button {
  padding: 0;
  background: transparent;
  cursor: pointer;
}

.swatch {
  display: inline-block;
  width: 2.2rem;
  height: 0.45rem;
  border-radius: 999px;
  margin-bottom: 0.75rem;
}

.position-card {
  padding: 0.95rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
}

.position-card-head span {
  font-size: 1.3rem;
  font-weight: 900;
  color: #ffcd7a;
}

.slot-head-actions {
  display: flex;
  gap: 0.85rem;
  align-items: center;
}

@media (min-width: 900px) {
  .create-grid {
    grid-template-columns: minmax(0, 1fr) 92px auto;
  }

  .slot-builder {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .position-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
