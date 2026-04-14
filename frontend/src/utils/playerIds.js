export function normalizePlayerId(value) {
  return value == null ? '' : String(value)
}

export function playerIdsMatch(left, right) {
  return normalizePlayerId(left) === normalizePlayerId(right)
}

export function playerIdListIncludes(ids = [], target) {
  return ids.some((id) => playerIdsMatch(id, target))
}
