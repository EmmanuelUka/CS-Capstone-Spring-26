function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

async function getCsrfToken() {
  const response = await fetch('/api/csrf', {
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const payload = await response.json()
  return payload.csrfToken
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'include',
    ...options,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json()
}

async function mutateJson(url, method, body) {
  const csrfToken = await getCsrfToken()
  return requestJson(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: body ? JSON.stringify(body) : undefined,
  })
}

function createSlot(position, playerId = null) {
  return {
    id: `slot-${position.toLowerCase()}-${Math.random().toString(36).slice(2, 8)}`,
    position,
    playerId,
  }
}

export async function fetchPlayers() {
  return requestJson('/api/recruits')
}

export async function deletePlayerRecord(playerId) {
  await mutateJson(`/api/recruits/${playerId}`, 'DELETE')
}

export async function listShortlists() {
  const data = await requestJson('/api/shortlists')
  return Array.isArray(data) ? data : []
}

export async function createShortlistRecord({ name, color, positions }) {
  const shortlist = {
    name: name.trim() || 'Untitled Group',
    color: color || '#ffb75e',
    slots: positions.map((position) => createSlot(position)),
  }

  const data = await mutateJson('/api/shortlists', 'POST', shortlist)
  return deepClone(data.shortlist)
}

export async function deleteShortlistRecord(shortlistId) {
  await mutateJson(`/api/shortlists/${shortlistId}`, 'DELETE')
}

export async function assignPlayerToShortlist(shortlistId, position, playerId) {
  await mutateJson(`/api/shortlists/${shortlistId}/assign_player`, 'POST', {
    position,
    playerId,
  })
}

export async function clearPlayerFromShortlist(shortlistId, slotId) {
  await mutateJson(`/api/shortlists/${shortlistId}/clear_player`, 'POST', {
    slotId,
  })
}

export async function addShortlistSlot(shortlistId, position) {
  const data = await mutateJson(`/api/shortlists/${shortlistId}/slots`, 'POST', {
    position,
  })
  return deepClone(data.slot)
}

export async function removeShortlistSlot(shortlistId, slotId) {
  await mutateJson(`/api/shortlists/${shortlistId}/slots/${slotId}`, 'DELETE')
}

export async function listArchetypes() {
  const data = await requestJson('/api/archetypes')
  return Array.isArray(data) ? data : []
}

export async function createArchetypeRecord(archetype) {
  const data = await mutateJson('/api/archetypes', 'POST', archetype)
  return deepClone(data.archetype)
}

export async function deleteArchetypeRecord(archetypeId) {
  await mutateJson(`/api/archetypes/${archetypeId}`, 'DELETE')
}
