import { reactive, watch } from 'vue'

import { EVAL_POSITIONS } from '../data/positionStats'
import { playerIdsMatch } from '../utils/playerIds'

const STORAGE_KEY = 'hashmark-recruiting-prototype'

const defaultFilters = {
  query: '',
  position: 'All',
  state: 'All',
  type: 'All',
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

const fallbackRosterPositions = [...new Set(EVAL_POSITIONS)].sort()
const rosterPositions = reactive([...fallbackRosterPositions])

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

function createSlotsForPositions(positions = []) {
  return positions
    .filter((position) => rosterPositions.includes(position))
    .map((position) => ({
      id: `slot-${position.toLowerCase()}-${Math.random().toString(36).slice(2, 8)}`,
      position,
      playerId: null,
    }))
}

function getPlayerByIdFromList(players, playerId) {
  return players.find((player) => playerIdsMatch(player.id, playerId)) || null
}

function refreshRosterPositions(playersList = []) {
  const nextPositions = [...new Set([...EVAL_POSITIONS, ...playersList.map((player) => player.position).filter(Boolean)])].sort()
  rosterPositions.splice(0, rosterPositions.length, ...(nextPositions.length ? nextPositions : fallbackRosterPositions))
}

function normalizeShortlist(list, playersList = []) {
  const slotPositions = Array.isArray(list.slots)
    ? list.slots.map((slot) => slot.position)
    : Array.isArray(list.playerIds)
      ? list.playerIds
          .map((playerId) => getPlayerByIdFromList(playersList, playerId)?.position)
          .filter(Boolean)
      : []
  const nextSlots = createSlotsForPositions(slotPositions.length ? slotPositions : rosterPositions)

  if (Array.isArray(list.slots)) {
    for (const slot of list.slots) {
      const target = nextSlots.find((entry) => !entry._claimed && entry.position === slot.position)
      if (
        target &&
        (playersList.length === 0 || getPlayerByIdFromList(playersList, slot.playerId)?.position === slot.position)
      ) {
        target.playerId = slot.playerId
      }
      if (target) {
        target.id = slot.id || target.id
        target._claimed = true
      }
    }
  } else if (Array.isArray(list.playerIds)) {
    for (const playerId of list.playerIds) {
      const player = getPlayerByIdFromList(playersList, playerId)
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
const persistedFilters = persisted.filters || {}
const normalizedPersistedFilters = {
  ...persistedFilters,
  type: persistedFilters.type || persistedFilters.evaluationStatus || 'All',
}

refreshRosterPositions()

const state = reactive({
  players: [],
  filters: {
    ...defaultFilters,
    ...normalizedPersistedFilters,
  },
  shortlists: (persisted.shortlists || []).map((list) => normalizeShortlist(list)),
  archetypes: persisted.archetypes || deepClone(defaultArchetypes),
  playersLoaded: false,
  playersLoading: false,
  playersError: '',
})

if (typeof window !== 'undefined') {
  watch(
    () => ({
      filters: state.filters,
      shortlists: state.shortlists,
      archetypes: state.archetypes,
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

function createShortlist({ name, color, positions }) {
  const fallbackPosition = rosterPositions[0]
  if (!fallbackPosition) {
    return
  }

  const shortlist = {
    id: `shortlist-${Date.now()}`,
    name: name.trim() || 'Untitled Group',
    color: color || '#ffb75e',
    slots: createSlotsForPositions(positions?.length ? positions : [fallbackPosition]),
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

let playersPromise = null

async function ensurePlayersLoaded() {
  if (state.playersLoaded) {
    return state.players
  }

  if (playersPromise) {
    return playersPromise
  }

  state.playersLoading = true
  state.playersError = ''

  playersPromise = fetch('/api/recruits', {
    credentials: 'include',
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const payload = await response.json()
      const nextPlayers = Array.isArray(payload.players) ? payload.players : []
      state.players = nextPlayers
      refreshRosterPositions(nextPlayers)
      state.shortlists = state.shortlists.map((list) => normalizeShortlist(list, nextPlayers))
      state.playersLoaded = true
      state.playersError = ''
      return nextPlayers
    })
    .catch((error) => {
      state.playersError = error.message || 'Unable to load players'
      throw error
    })
    .finally(() => {
      state.playersLoading = false
      playersPromise = null
    })

  return playersPromise
}

function getPlayerById(playerId) {
  return getPlayerByIdFromList(state.players, playerId)
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

export function useRecruitingStore() {
  return {
    state,
    ensurePlayersLoaded,
    getPlayerById,
    setFilters,
    resetFilters,
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
