import { playerIdsMatch } from '../utils/playerIds'

export const players = [
  {
    id: 1,
    name: 'Evan Brooks',
    school: 'St. Xavier',
    state: 'OH',
    city: 'Cincinnati',
    classYear: 2027,
    position: 'QB',
    projectedPosition: 'RPO Quarterback',
    evaluationStatus: 'Ready',
    height: "6'2\"",
    weight: 204,
    fortyTime: '4.68',
    gpa: 3.7,
    rating: 91,
    stars: 4,
    jersey: '#7',
    archetype: 'Field Commander',
    summary:
      'Quick processor with strong middle-of-field accuracy and enough mobility to keep zone-read tags live.',
    explanation:
      'Best fit in a spread system that wants early-decision throws, designed movement, and efficient third-down answers.',
    notes:
      'High-volume thrower with clean mechanics. Coaches flagged leadership and poise as early separators.',
    schemeFit: 93,
    comparisonScore: 92,
    confidenceScore: 88,
    breakdown: {
      physical: 82,
      athletic: 79,
      production: 94,
      context: 87,
    },
    stats: {
      passingYards: 3248,
      touchdowns: 34,
      interceptions: 6,
      rushYards: 512,
    },
    topComparables: [4, 6, 7],
  },
  {
    id: 2,
    name: 'Malik Dorsey',
    school: 'Buford',
    state: 'GA',
    city: 'Buford',
    classYear: 2027,
    position: 'WR',
    projectedPosition: 'Boundary X Receiver',
    evaluationStatus: 'Compare',
    height: "6'3\"",
    weight: 196,
    fortyTime: '4.43',
    gpa: 3.4,
    rating: 94,
    stars: 4,
    jersey: '#1',
    archetype: 'Vertical Winner',
    summary:
      'Explosive outside target who wins stacked releases, tracks the deep ball, and creates red-zone leverage.',
    explanation:
      'Prototype boundary receiver for an offense that wants isolated shot plays and a back-shoulder answer on money downs.',
    notes:
      'Elite acceleration off the line. Needs more polish on underneath pacing but already changes coverage structure.',
    schemeFit: 95,
    comparisonScore: 94,
    confidenceScore: 90,
    breakdown: {
      physical: 86,
      athletic: 94,
      production: 89,
      context: 85,
    },
    stats: {
      receptions: 71,
      receivingYards: 1284,
      touchdowns: 16,
      contestedCatchRate: '68%',
    },
    topComparables: [5, 6, 4],
  },
  {
    id: 3,
    name: 'Isaiah Ford',
    school: 'IMG Academy',
    state: 'FL',
    city: 'Bradenton',
    classYear: 2027,
    position: 'LB',
    projectedPosition: 'Run-and-Chase Mike',
    evaluationStatus: 'Ready',
    height: "6'1\"",
    weight: 228,
    fortyTime: '4.59',
    gpa: 3.6,
    rating: 89,
    stars: 3,
    jersey: '#32',
    archetype: 'Front-Seven Eraser',
    summary:
      'Trigger-fast second-level defender with strong pursuit angles and reliable finish technique.',
    explanation:
      'Profiles as a middle linebacker in pressure packages where range and closing speed matter more than pure size.',
    notes:
      'Very clean diagnostic tape. One of the safest defensive evaluations in the board.',
    schemeFit: 91,
    comparisonScore: 90,
    confidenceScore: 92,
    breakdown: {
      physical: 81,
      athletic: 90,
      production: 88,
      context: 89,
    },
    stats: {
      tackles: 117,
      tacklesForLoss: 18,
      sacks: 6,
      forcedFumbles: 3,
    },
    topComparables: [7, 5, 1],
  },
  {
    id: 4,
    name: 'Tyler Morris',
    school: 'North Shore',
    state: 'TX',
    city: 'Houston',
    classYear: 2026,
    position: 'QB',
    projectedPosition: 'Pocket Distributor',
    evaluationStatus: 'Watch',
    height: "6'4\"",
    weight: 212,
    fortyTime: '4.84',
    gpa: 3.8,
    rating: 87,
    stars: 3,
    jersey: '#12',
    archetype: 'Timing Thrower',
    summary:
      'Tall pocket passer with advanced anticipation and clean footwork in structured dropback concepts.',
    explanation:
      'Best fit in a timing-based offense that majors in play-action, deeper dig windows, and controlled movement.',
    notes:
      'Less dynamic outside structure, but the floor is high because of processing and touch.',
    schemeFit: 88,
    comparisonScore: 86,
    confidenceScore: 84,
    breakdown: {
      physical: 84,
      athletic: 71,
      production: 85,
      context: 88,
    },
    stats: {
      passingYards: 2987,
      touchdowns: 27,
      interceptions: 8,
      completionRate: '68%',
    },
    topComparables: [1, 6, 7],
  },
  {
    id: 5,
    name: 'Jalen Strickland',
    school: 'Cass Tech',
    state: 'MI',
    city: 'Detroit',
    classYear: 2026,
    position: 'CB',
    projectedPosition: 'Press Corner',
    evaluationStatus: 'Ready',
    height: "6'0\"",
    weight: 184,
    fortyTime: '4.41',
    gpa: 3.5,
    rating: 90,
    stars: 4,
    jersey: '#4',
    archetype: 'Mirror Corner',
    summary:
      'Length, patience, and recovery burst show up immediately against high-level wideouts.',
    explanation:
      'Strong match for a defense that wants man coverage flexibility and trusts corners to challenge the release.',
    notes:
      'Ball production climbed late. Still adding lower-body power but the coverage traits are real.',
    schemeFit: 92,
    comparisonScore: 89,
    confidenceScore: 87,
    breakdown: {
      physical: 80,
      athletic: 93,
      production: 84,
      context: 86,
    },
    stats: {
      passBreakups: 14,
      interceptions: 5,
      tackles: 39,
      completionAllowed: '38%',
    },
    topComparables: [2, 3, 7],
  },
  {
    id: 6,
    name: 'Caden Price',
    school: 'Bishop Gorman',
    state: 'NV',
    city: 'Las Vegas',
    classYear: 2027,
    position: 'TE',
    projectedPosition: 'Move Tight End',
    evaluationStatus: 'Compare',
    height: "6'5\"",
    weight: 232,
    fortyTime: '4.61',
    gpa: 3.9,
    rating: 88,
    stars: 4,
    jersey: '#86',
    archetype: 'Flex Mismatch',
    summary:
      'Long, fluid pass catcher who threatens seams, flex alignments, and third-down mismatch packages.',
    explanation:
      'Ideal for a coordinator who wants a detached tight end to stress linebackers without sacrificing red-zone size.',
    notes:
      'Route pacing is ahead of schedule. Blocking profile is developmental but usable in motion-heavy looks.',
    schemeFit: 90,
    comparisonScore: 88,
    confidenceScore: 85,
    breakdown: {
      physical: 88,
      athletic: 86,
      production: 80,
      context: 82,
    },
    stats: {
      receptions: 49,
      receivingYards: 811,
      touchdowns: 11,
      yardsAfterCatch: 241,
    },
    topComparables: [2, 4, 1],
  },
  {
    id: 7,
    name: 'Miles Turner',
    school: 'St. Frances Academy',
    state: 'MD',
    city: 'Baltimore',
    classYear: 2026,
    position: 'EDGE',
    projectedPosition: 'Stand-up Edge',
    evaluationStatus: 'Watch',
    height: "6'4\"",
    weight: 241,
    fortyTime: '4.66',
    gpa: 3.2,
    rating: 86,
    stars: 3,
    jersey: '#9',
    archetype: 'Pressure Specialist',
    summary:
      'Long outside rusher with real first-step speed and enough bend to threaten the corner.',
    explanation:
      'High-variance edge prospect who fits best in an aggressive front that creates wide rush tracks and games.',
    notes:
      'Pass-rush flashes are premium. Needs more snap-to-snap consistency against the run.',
    schemeFit: 84,
    comparisonScore: 85,
    confidenceScore: 79,
    breakdown: {
      physical: 83,
      athletic: 88,
      production: 77,
      context: 80,
    },
    stats: {
      sacks: 11,
      pressures: 36,
      tacklesForLoss: 15,
      qbHits: 19,
    },
    topComparables: [3, 5, 2],
  },
]

export const shortlists = [
  {
    id: 'priority-board',
    name: 'Priority Board',
    color: '#ffb75e',
    slots: [
      { position: 'QB', playerId: 1 },
      { position: 'WR', playerId: 2 },
      { position: 'CB', playerId: 5 },
    ],
  },
  {
    id: 'midwest-targets',
    name: 'Midwest Targets',
    color: '#79c8ff',
    slots: [
      { position: 'QB', playerId: 1 },
      { position: 'LB', playerId: 3 },
      { position: 'CB', playerId: 5 },
    ],
  },
  {
    id: 'late-cycle',
    name: 'Late Cycle Values',
    color: '#8dd8a7',
    slots: [
      { position: 'QB', playerId: 4 },
      { position: 'EDGE', playerId: 7 },
    ],
  },
]

export const activityFeed = [
  {
    id: 'act-1',
    label: 'Comparison run completed',
    detail: 'Evan Brooks vs Tyler Morris updated with a new production edge.',
    time: '12 min ago',
  },
  {
    id: 'act-2',
    label: 'Shortlist updated',
    detail: 'Malik Dorsey moved into Priority Board after spring eval.',
    time: '35 min ago',
  },
  {
    id: 'act-3',
    label: 'Coach note added',
    detail: 'Isaiah Ford tagged as a fit for pressure-heavy packages.',
    time: '1 hr ago',
  },
  {
    id: 'act-4',
    label: 'Visit scheduled',
    detail: 'Caden Price set for on-campus June visit.',
    time: 'Today',
  },
]

export function getPlayerById(playerId) {
  return players.find((player) => playerIdsMatch(player.id, playerId)) || null
}

export function getPlayersByIds(ids = []) {
  return ids.map((id) => getPlayerById(id)).filter(Boolean)
}

export function getComparables(player) {
  return getPlayersByIds(player?.topComparables || [])
}
