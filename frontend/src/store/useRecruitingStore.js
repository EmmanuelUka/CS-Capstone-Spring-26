import { computed, reactive, watch } from 'vue'

import { EVAL_POSITIONS } from '../data/positionStats'
import { normalizePlayerId, playerIdListIncludes, playerIdsMatch } from '../utils/playerIds'

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

function averageScores(scores = {}) {
  const values = Object.values(scores).filter((value) => typeof value === 'number')
  if (!values.length) {
    return 0
  }

  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length)
}

function createHistoricalPlayers(historicalMatchesByRecruitId = {}) {
  return Object.values(historicalMatchesByRecruitId)
    .flat()
    .map((match) => ({
      id: match.historicalId,
      isHistorical: true,
      name: match.name,
      school: match.school,
      state: match.conference,
      city: '',
      classYear: match.lastSeason,
      position: match.position,
      projectedPosition: `Historical ${match.position} Comparable`,
      type: 'Historical',
      height: 'N/A',
      weight: null,
      fortyTime: 'N/A',
      gpa: null,
      rating: averageScores(match.comparisonScores),
      stars: 0,
      jersey: 'HIST',
      archetype: 'Historical Match',
      summary: `Historical comparable from ${match.school} in the ${match.conference}.`,
      explanation: 'This record captures how closely the historical player matches the selected recruit profile.',
      notes: `Most recent recorded season: ${match.lastSeason}. Historical player cards do not include related-athlete suggestions.`,
      schemeFit: averageScores(match.comparisonScores),
      comparisonScore: averageScores(match.comparisonScores),
      confidenceScore: averageScores(match.comparisonScores),
      breakdown: {
        physical: match.comparisonScores?.physical,
        production: match.comparisonScores?.production,
        context: match.comparisonScores?.context,
      },
      stats: {
        conference: match.conference,
        lastSeason: match.lastSeason,
        superScore: averageScores(match.comparisonScores),
      },
      topComparables: [],
    }))
}

function getHistoricalMatchesForData(historicalMatchesByRecruitId = {}, playerId) {
  return [...(historicalMatchesByRecruitId[normalizePlayerId(playerId)] || [])]
    .map((match) => ({
      ...match,
      superScore:
        typeof match.superScore === 'number' ? match.superScore : averageScores(match.comparisonScores),
    }))
    .sort((left, right) => right.superScore - left.superScore)
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
  historicalMatchesByRecruitId: {},
  historicalPlayers: [],
  filters: {
    ...defaultFilters,
    ...normalizedPersistedFilters,
  },
  shortlists: (persisted.shortlists || []).map((list) => normalizeShortlist(list)),
  archetypes: persisted.archetypes || deepClone(defaultArchetypes),
  compareSelection:
    persisted.compareSelection && persisted.compareSelection.length
      ? persisted.compareSelection
      : [],
  exampleDataLoaded: false,
  exampleDataLoading: false,
  exampleDataError: '',
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
  const uniqueIds = [...new Set(ids.map(normalizePlayerId).filter((id) => getPlayerById(id)))]
  state.compareSelection = uniqueIds
}

function toggleComparePlayer(playerId) {
  const normalizedPlayerId = normalizePlayerId(playerId)

  if (playerIdListIncludes(state.compareSelection, normalizedPlayerId)) {
    state.compareSelection = state.compareSelection.filter(
      (id) => !playerIdsMatch(id, normalizedPlayerId)
    )
    return
  }

  state.compareSelection = [...state.compareSelection, normalizedPlayerId]
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

function hydrateExampleData(payload = {}) {
  const nextPlayers = Array.isArray(payload.players) ? payload.players : []
  const nextHistoricalMatches = payload.historicalMatches && typeof payload.historicalMatches === 'object'
    ? Object.fromEntries(
        Object.entries(payload.historicalMatches).map(([playerId, matches]) => [
          normalizePlayerId(playerId),
          Array.isArray(matches) ? matches : [],
        ])
      )
    : {}

  state.players = nextPlayers
  refreshRosterPositions(nextPlayers)
  state.historicalMatchesByRecruitId = nextHistoricalMatches
  state.historicalPlayers = createHistoricalPlayers(nextHistoricalMatches)

  const nextShortlists = persisted.shortlists
    ? persisted.shortlists
    : Array.isArray(payload.shortlists)
      ? payload.shortlists
      : []
  state.shortlists = nextShortlists.map((list) => normalizeShortlist(list, nextPlayers))

  state.compareSelection = state.compareSelection.filter((id) => getPlayerByIdFromList(nextPlayers, id))

  state.exampleDataLoaded = true
  state.exampleDataError = ''
}

let exampleDataPromise = null

async function ensureExampleDataLoaded() {
  if (state.exampleDataLoaded) {
    return state
  }

  if (exampleDataPromise) {
    return exampleDataPromise
  }

  state.exampleDataLoading = true
  state.exampleDataError = ''

  exampleDataPromise = fetch('/api/example_recruiting_data', {
    credentials: 'include',
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const payload = await response.json()
      hydrateExampleData(payload)
      return state
    })
    .catch((error) => {
      state.exampleDataError = error.message || 'Unable to load example data'
      state.exampleDataLoaded = true
      return state
    })
    .finally(() => {
      state.exampleDataLoading = false
      exampleDataPromise = null
    })

  return exampleDataPromise
}

function getPlayerById(playerId) {
  return getPlayerByIdFromList(state.players, playerId)
}

function getHistoricalPlayerById(playerId) {
  return state.historicalPlayers.find((player) => playerIdsMatch(player.id, playerId)) || null
}

function getDisplayPlayerById(playerId) {
  return getPlayerById(playerId) || getHistoricalPlayerById(playerId)
}

function getComparables(player) {
  return (player?.topComparables || []).map((id) => getPlayerById(id)).filter(Boolean)
}

function getHistoricalMatches(playerId) {
  return getHistoricalMatchesForData(state.historicalMatchesByRecruitId, playerId)
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
    const matchesType = state.filters.type === 'All' || player.type === state.filters.type
    const matchesRating = player.rating >= state.filters.ratingFloor

    return matchesQuery && matchesPosition && matchesState && matchesType && matchesRating
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
    ensureExampleDataLoaded,
    getPlayerById,
    getDisplayPlayerById,
    getComparables,
    getHistoricalMatches,
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
