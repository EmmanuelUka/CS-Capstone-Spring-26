import { computed, reactive, watch } from 'vue'

import {
  getPlayerById,
  players,
  shortlists as defaultShortlists,
} from '../data/mockRecruitingData'

const STORAGE_KEY = 'hashmark-recruiting-prototype'

const defaultFilters = {
  query: '',
  position: 'All',
  state: 'All',
  evaluationStatus: 'All',
  ratingFloor: 0,
}

const defaultArchetypes = [
  {
    id: 'archetype-running-qb',
    name: 'Running QB',
    position: 'QB',
    notes: 'Dual-threat quarterback profile for zone-read and designed movement packages.',
    minimums: [
      { statKey: 'rushYards', minValue: 350 },
      { statKey: 'passingYards', minValue: 2200 },
    ],
  },
  {
    id: 'archetype-boundary-x',
    name: 'Boundary X',
    position: 'WR',
    notes: 'Outside receiver profile for vertical shots and red-zone isolation.',
    minimums: [
      { statKey: 'receivingYards', minValue: 900 },
      { statKey: 'touchdowns', minValue: 10 },
    ],
  },
]

const rosterPositions = [...new Set(players.map((player) => player.position))].sort()

function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

function loadPersistedState() {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function createEmptySlots() {
  return rosterPositions.map((position) => ({
    id: `slot-${position.toLowerCase()}-${Math.random().toString(36).slice(2, 8)}`,
    position,
    playerId: null,
  }))
}

function createSlotsForPositions(positions = []) {
  return positions
    .filter((position) => rosterPositions.includes(position))
    .map((position) => ({
      id: `slot-${position.toLowerCase()}-${Math.random().toString(36).slice(2, 8)}`,
      position,
      playerId: null,
    }))
}

function normalizeShortlist(list) {
  const slotPositions = Array.isArray(list.slots)
    ? list.slots.map((slot) => slot.position)
    : Array.isArray(list.playerIds)
      ? list.playerIds
          .map((playerId) => getPlayerById(playerId)?.position)
          .filter(Boolean)
      : []
  const nextSlots = createSlotsForPositions(slotPositions.length ? slotPositions : rosterPositions)

  if (Array.isArray(list.slots)) {
    for (const slot of list.slots) {
      const target = nextSlots.find((entry) => !entry._claimed && entry.position === slot.position)
      if (target && getPlayerById(slot.playerId)?.position === slot.position) {
        target.playerId = slot.playerId
      }
      if (target) {
        target.id = slot.id || target.id
        target._claimed = true
      }
    }
  } else if (Array.isArray(list.playerIds)) {
    for (const playerId of list.playerIds) {
      const player = getPlayerById(playerId)
      const target = nextSlots.find((entry) => !entry._claimed && entry.position === player?.position)
      if (player && target && !target.playerId) {
        target.playerId = player.id
        target._claimed = true
      }
    }
  }

  return {
    id: list.id,
    name: list.name,
    color: list.color || '#ffb75e',
    slots: nextSlots.map(({ _claimed, ...slot }) => slot),
  }
}

const persisted = loadPersistedState()

const state = reactive({
  players,
  filters: {
    ...defaultFilters,
    ...(persisted.filters || {}),
  },
  shortlists: (persisted.shortlists || deepClone(defaultShortlists)).map(normalizeShortlist),
  archetypes: persisted.archetypes || deepClone(defaultArchetypes),
  compareSelection:
    persisted.compareSelection && persisted.compareSelection.length
      ? persisted.compareSelection
      : ['evan-brooks', 'malik-dorsey'],
  ready: true,
})

if (typeof window !== 'undefined') {
  watch(
    () => ({
      filters: state.filters,
      shortlists: state.shortlists,
      archetypes: state.archetypes,
      compareSelection: state.compareSelection,
    }),
    (value) => {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    },
    { deep: true }
  )
}

function setFilters(nextFilters) {
  state.filters = {
    ...state.filters,
    ...nextFilters,
  }
}

function resetFilters() {
  state.filters = { ...defaultFilters }
}

function setCompareSelection(ids) {
  const uniqueIds = [...new Set(ids.filter((id) => getPlayerById(id)))]
  state.compareSelection = uniqueIds
}

function toggleComparePlayer(playerId) {
  if (state.compareSelection.includes(playerId)) {
    state.compareSelection = state.compareSelection.filter((id) => id !== playerId)
    return
  }

  state.compareSelection = [...state.compareSelection, playerId]
}

function createShortlist({ name, color, positions }) {
  const shortlist = {
    id: `shortlist-${Date.now()}`,
    name: name.trim() || 'Untitled Group',
    color: color || '#ffb75e',
    slots: createSlotsForPositions(positions?.length ? positions : [rosterPositions[0]]),
  }
  state.shortlists = [shortlist, ...state.shortlists]
}

function deleteShortlist(shortlistId) {
  state.shortlists = state.shortlists.filter((list) => list.id !== shortlistId)
}

function addPlayerToShortlist(shortlistId, position, playerId) {
  const player = getPlayerById(playerId)

  if (!player || player.position !== position) {
    return
  }

  state.shortlists = state.shortlists.map((list) =>
    list.id !== shortlistId
      ? list
      : {
          ...list,
          slots: list.slots.map((slot) =>
            slot.position !== position ? slot : { ...slot, playerId }
          ),
        }
  )
}

function removePlayerFromShortlist(shortlistId, slotId) {
  state.shortlists = state.shortlists.map((list) =>
    list.id !== shortlistId
      ? list
      : {
          ...list,
          slots: list.slots.map((slot) =>
            slot.id !== slotId ? slot : { ...slot, playerId: null }
          ),
        }
  )
}

function addPositionSlot(shortlistId, position) {
  if (!rosterPositions.includes(position)) {
    return
  }

  state.shortlists = state.shortlists.map((list) =>
    list.id !== shortlistId
      ? list
      : {
          ...list,
          slots: [...list.slots, ...createSlotsForPositions([position])],
        }
  )
}

function removePositionSlot(shortlistId, slotId) {
  state.shortlists = state.shortlists.map((list) =>
    list.id !== shortlistId
      ? list
      : {
          ...list,
          slots: list.slots.filter((slot) => slot.id !== slotId),
        }
  )
}

function createArchetype({ name, position, notes, minimums }) {
  const normalizedMinimums = (minimums || [])
    .filter((rule) => rule?.statKey && Number.isFinite(Number(rule.minValue)))
    .map((rule) => ({
      statKey: rule.statKey,
      minValue: Number(rule.minValue),
    }))

  if (!position || !normalizedMinimums.length) {
    return
  }

  const archetype = {
    id: `archetype-${Date.now()}`,
    name: name?.trim() || `${position} Archetype`,
    position,
    notes: notes?.trim() || '',
    minimums: normalizedMinimums,
  }

  state.archetypes = [archetype, ...state.archetypes]
}

function deleteArchetype(archetypeId) {
  state.archetypes = state.archetypes.filter((archetype) => archetype.id !== archetypeId)
}

const filteredPlayers = computed(() =>
  state.players.filter((player) => {
    const query = state.filters.query.trim().toLowerCase()
    const matchesQuery =
      !query ||
      [player.name, player.school, player.city]
        .join(' ')
        .toLowerCase()
        .includes(query)

    const matchesPosition =
      state.filters.position === 'All' || player.position === state.filters.position
    const matchesState = state.filters.state === 'All' || player.state === state.filters.state
    const matchesStatus =
      state.filters.evaluationStatus === 'All' ||
      player.evaluationStatus === state.filters.evaluationStatus
    const matchesRating = player.rating >= state.filters.ratingFloor

    return matchesQuery && matchesPosition && matchesState && matchesStatus && matchesRating
  })
)

const comparePlayers = computed(() =>
  state.compareSelection.map((id) => getPlayerById(id)).filter(Boolean)
)

export function useRecruitingStore() {
  return {
    state,
    filteredPlayers,
    comparePlayers,
    setFilters,
    resetFilters,
    setCompareSelection,
    toggleComparePlayer,
    createShortlist,
    deleteShortlist,
    addPlayerToShortlist,
    removePlayerFromShortlist,
    addPositionSlot,
    removePositionSlot,
    createArchetype,
    deleteArchetype,
    rosterPositions,
  }
}
