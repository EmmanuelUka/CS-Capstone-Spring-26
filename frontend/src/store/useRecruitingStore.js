import { reactive } from 'vue'

import { EVAL_POSITIONS } from '../data/positionStats'
import { playerIdsMatch } from '../utils/playerIds'
import {
  addShortlistSlot,
  assignPlayerToShortlist,
  clearPlayerFromShortlist,
  createArchetypeRecord,
  createShortlistRecord,
  deleteArchetypeRecord,
  deleteShortlistRecord,
  fetchPlayers,
  listArchetypes,
  listShortlists,
  removeShortlistSlot,
} from '../services/recruitingClient'

const defaultFilters = {
  query: '',
  position: 'All',
  state: 'All',
  type: 'All',
  ratingFloor: 0,
}

const fallbackRosterPositions = [...new Set(EVAL_POSITIONS)].sort()
const rosterPositions = reactive([...fallbackRosterPositions])

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
  }

  return {
    id: list.id,
    name: list.name,
    color: list.color || '#ffb75e',
    slots: nextSlots.map(({ _claimed, ...slot }) => slot),
  }
}

refreshRosterPositions()

const state = reactive({
  players: [],
  filters: { ...defaultFilters },
  shortlists: [],
  archetypes: [],
  playersLoaded: false,
  playersLoading: false,
  playersError: '',
  shortlistsLoaded: false,
  shortlistsLoading: false,
  shortlistsError: '',
  archetypesLoaded: false,
  archetypesLoading: false,
  archetypesError: '',
})

function setFilters(nextFilters) {
  state.filters = {
    ...state.filters,
    ...nextFilters,
  }
}

function resetFilters() {
  state.filters = { ...defaultFilters }
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

  playersPromise = fetchPlayers()
    .then((payload) => {
      const nextPlayers = Array.isArray(payload.players) ? payload.players : []
      state.players = nextPlayers
      refreshRosterPositions(nextPlayers)
      state.shortlists = state.shortlists.map((list) => normalizeShortlist(list, nextPlayers))
      state.playersLoaded = true
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

let shortlistsPromise = null

async function ensureShortlistsLoaded() {
  if (state.shortlistsLoaded) {
    return state.shortlists
  }

  if (shortlistsPromise) {
    return shortlistsPromise
  }

  state.shortlistsLoading = true
  state.shortlistsError = ''

  shortlistsPromise = listShortlists()
    .then((shortlists) => {
      state.shortlists = shortlists.map((list) => normalizeShortlist(list, state.players))
      state.shortlistsLoaded = true
      return state.shortlists
    })
    .catch((error) => {
      state.shortlistsError = error.message || 'Unable to load shortlists'
      throw error
    })
    .finally(() => {
      state.shortlistsLoading = false
      shortlistsPromise = null
    })

  return shortlistsPromise
}

let archetypesPromise = null

async function ensureArchetypesLoaded() {
  if (state.archetypesLoaded) {
    return state.archetypes
  }

  if (archetypesPromise) {
    return archetypesPromise
  }

  state.archetypesLoading = true
  state.archetypesError = ''

  archetypesPromise = listArchetypes()
    .then((archetypes) => {
      state.archetypes = archetypes
      state.archetypesLoaded = true
      return archetypes
    })
    .catch((error) => {
      state.archetypesError = error.message || 'Unable to load archetypes'
      throw error
    })
    .finally(() => {
      state.archetypesLoading = false
      archetypesPromise = null
    })

  return archetypesPromise
}

function getPlayerById(playerId) {
  return getPlayerByIdFromList(state.players, playerId)
}

async function createShortlist({ name, color, positions }) {
  const nextPositions = (positions?.length ? positions : [rosterPositions[0]]).filter(Boolean)
  if (!nextPositions.length) {
    return
  }

  const shortlist = await createShortlistRecord({
    name,
    color,
    positions: nextPositions,
  })
  state.shortlists = [normalizeShortlist(shortlist, state.players), ...state.shortlists]
  state.shortlistsLoaded = true
}

async function deleteShortlist(shortlistId) {
  await deleteShortlistRecord(shortlistId)
  state.shortlists = state.shortlists.filter((list) => list.id !== shortlistId)
  state.shortlistsLoaded = true
}

async function addPlayerToShortlist(shortlistId, position, playerId) {
  const player = getPlayerById(playerId)

  if (!player || player.position !== position) {
    return
  }

  await assignPlayerToShortlist(shortlistId, position, playerId)
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
  state.shortlistsLoaded = true
}

async function removePlayerFromShortlist(shortlistId, slotId) {
  await clearPlayerFromShortlist(shortlistId, slotId)
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
  state.shortlistsLoaded = true
}

async function addPositionSlot(shortlistId, position) {
  if (!rosterPositions.includes(position)) {
    return
  }

  const slot = await addShortlistSlot(shortlistId, position)
  state.shortlists = state.shortlists.map((list) =>
    list.id !== shortlistId
      ? list
      : {
          ...list,
          slots: [...list.slots, slot],
        }
  )
  state.shortlistsLoaded = true
}

async function removePositionSlot(shortlistId, slotId) {
  await removeShortlistSlot(shortlistId, slotId)
  state.shortlists = state.shortlists.map((list) =>
    list.id !== shortlistId
      ? list
      : {
          ...list,
          slots: list.slots.filter((slot) => slot.id !== slotId),
        }
  )
  state.shortlistsLoaded = true
}

async function createArchetype({ name, position, notes, minimums }) {
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

  await createArchetypeRecord(archetype)
  state.archetypes = [archetype, ...state.archetypes]
  state.archetypesLoaded = true
}

async function deleteArchetype(archetypeId) {
  await deleteArchetypeRecord(archetypeId)
  state.archetypes = state.archetypes.filter((archetype) => archetype.id !== archetypeId)
  state.archetypesLoaded = true
}

export function useRecruitingStore() {
  return {
    state,
    ensurePlayersLoaded,
    ensureShortlistsLoaded,
    ensureArchetypesLoaded,
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
