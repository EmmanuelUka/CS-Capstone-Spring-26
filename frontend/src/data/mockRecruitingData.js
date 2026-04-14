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
    type: 'High School',
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
    type: 'High School',
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
    type: 'High School',
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
    type: 'Transfer',
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
    type: 'High School',
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
    type: 'Transfer',
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
    type: 'High School',
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

const historicalComparisonMap = {
  1: [
    {
      historicalId: 'qb-hist-1',
      name: 'Jordan Reeves',
      position: 'QB',
      school: 'Oklahoma State',
      conference: 'Big 12',
      lastSeason: 2023,
      comparisonScores: {
        physical: 90,
        production: 93,
        context: 84,
      },
    },
    {
      historicalId: 'qb-hist-2',
      name: 'Malik James',
      position: 'QB',
      school: 'Appalachian State',
      conference: 'Sun Belt',
      lastSeason: 2023,
      comparisonScores: {
        physical: 87,
        production: 85,
        context: 80,
      },
    },
    {
      historicalId: 'qb-hist-3',
      name: 'Connor Hale',
      position: 'QB',
      school: 'Kansas State',
      conference: 'Big 12',
      lastSeason: 2021,
      comparisonScores: {
        physical: 82,
        production: 88,
        context: 79,
      },
    },
  ],
  2: [
    {
      historicalId: 'wr-hist-1',
      name: 'Marcus Hill',
      position: 'WR',
      school: 'Georgia',
      conference: 'SEC',
      lastSeason: 2023,
      comparisonScores: {
        physical: 89,
        production: 92,
        context: 88,
      },
    },
    {
      historicalId: 'wr-hist-2',
      name: 'Tyler Owens',
      position: 'WR',
      school: 'Michigan State',
      conference: 'Big Ten',
      lastSeason: 2018,
      comparisonScores: {
        physical: 86,
        production: 89,
        context: 83,
      },
    },
    {
      historicalId: 'wr-hist-3',
      name: 'DeShawn Brooks',
      position: 'WR',
      school: 'Toledo',
      conference: 'MAC',
      lastSeason: 2023,
      comparisonScores: {
        physical: 82,
        production: 84,
        context: 78,
      },
    },
  ],
  3: [
    {
      historicalId: 'lb-hist-1',
      name: 'Andre Wallace',
      position: 'LB',
      school: 'Wisconsin',
      conference: 'Big Ten',
      lastSeason: 2022,
      comparisonScores: {
        physical: 84,
        production: 90,
        context: 87,
      },
    },
    {
      historicalId: 'lb-hist-2',
      name: 'Micah Benton',
      position: 'LB',
      school: 'Kentucky',
      conference: 'SEC',
      lastSeason: 2023,
      comparisonScores: {
        physical: 82,
        production: 88,
        context: 85,
      },
    },
    {
      historicalId: 'lb-hist-3',
      name: 'Cole Mercer',
      position: 'LB',
      school: 'Iowa',
      conference: 'Big Ten',
      lastSeason: 2021,
      comparisonScores: {
        physical: 79,
        production: 85,
        context: 84,
      },
    },
  ],
  4: [
    {
      historicalId: 'qb-hist-4',
      name: 'Ethan Wade',
      position: 'QB',
      school: 'Wake Forest',
      conference: 'ACC',
      lastSeason: 2022,
      comparisonScores: {
        physical: 88,
        production: 84,
        context: 86,
      },
    },
    {
      historicalId: 'qb-hist-5',
      name: 'Jordan Reeves',
      position: 'QB',
      school: 'Oklahoma State',
      conference: 'Big 12',
      lastSeason: 2023,
      comparisonScores: {
        physical: 86,
        production: 82,
        context: 88,
      },
    },
    {
      historicalId: 'qb-hist-6',
      name: 'Parker Sloan',
      position: 'QB',
      school: 'BYU',
      conference: 'Big 12',
      lastSeason: 2020,
      comparisonScores: {
        physical: 83,
        production: 80,
        context: 84,
      },
    },
  ],
  5: [
    {
      historicalId: 'cb-hist-1',
      name: 'Kris Vaughn',
      position: 'CB',
      school: 'LSU',
      conference: 'SEC',
      lastSeason: 2023,
      comparisonScores: {
        physical: 85,
        production: 88,
        context: 84,
      },
    },
    {
      historicalId: 'cb-hist-2',
      name: 'Darius Cole',
      position: 'CB',
      school: 'Michigan',
      conference: 'Big Ten',
      lastSeason: 2022,
      comparisonScores: {
        physical: 83,
        production: 86,
        context: 82,
      },
    },
    {
      historicalId: 'cb-hist-3',
      name: 'Tre Holloway',
      position: 'CB',
      school: 'Louisville',
      conference: 'ACC',
      lastSeason: 2021,
      comparisonScores: {
        physical: 80,
        production: 84,
        context: 81,
      },
    },
  ],
  6: [
    {
      historicalId: 'te-hist-1',
      name: 'Logan Cross',
      position: 'TE',
      school: 'Utah',
      conference: 'Pac-12',
      lastSeason: 2023,
      comparisonScores: {
        physical: 91,
        production: 83,
        context: 82,
      },
    },
    {
      historicalId: 'te-hist-2',
      name: 'Brady Shelton',
      position: 'TE',
      school: 'Notre Dame',
      conference: 'Independent',
      lastSeason: 2022,
      comparisonScores: {
        physical: 88,
        production: 80,
        context: 79,
      },
    },
    {
      historicalId: 'te-hist-3',
      name: 'Mason Pike',
      position: 'TE',
      school: 'Kansas State',
      conference: 'Big 12',
      lastSeason: 2021,
      comparisonScores: {
        physical: 84,
        production: 78,
        context: 77,
      },
    },
  ],
  7: [
    {
      historicalId: 'edge-hist-1',
      name: 'Jermaine Pratt',
      position: 'EDGE',
      school: 'Penn State',
      conference: 'Big Ten',
      lastSeason: 2023,
      comparisonScores: {
        physical: 86,
        production: 82,
        context: 80,
      },
    },
    {
      historicalId: 'edge-hist-2',
      name: 'Quincy Reed',
      position: 'EDGE',
      school: 'Ole Miss',
      conference: 'SEC',
      lastSeason: 2022,
      comparisonScores: {
        physical: 84,
        production: 79,
        context: 83,
      },
    },
    {
      historicalId: 'edge-hist-3',
      name: 'Damon Graves',
      position: 'EDGE',
      school: 'NC State',
      conference: 'ACC',
      lastSeason: 2021,
      comparisonScores: {
        physical: 82,
        production: 77,
        context: 78,
      },
    },
  ],
}

function averageScores(scores = {}) {
  const values = Object.values(scores).filter((value) => typeof value === 'number')
  if (!values.length) {
    return 0
  }

  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length)
}

const historicalPlayers = Object.values(historicalComparisonMap)
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
    explanation: `This record captures how closely the historical player matches the selected recruit profile.`,
    notes: `Most recent recorded season: ${match.lastSeason}. Historical player cards do not include related-athlete suggestions.`,
    schemeFit: averageScores(match.comparisonScores),
    comparisonScore: averageScores(match.comparisonScores),
    confidenceScore: averageScores(match.comparisonScores),
    breakdown: {
      physical: match.comparisonScores.physical,
      production: match.comparisonScores.production,
      context: match.comparisonScores.context,
    },
    stats: {
      conference: match.conference,
      lastSeason: match.lastSeason,
      superScore: averageScores(match.comparisonScores),
    },
    topComparables: [],
  }))

export function getPlayerById(playerId) {
  return players.find((player) => playerIdsMatch(player.id, playerId)) || null
}

export function getPlayersByIds(ids = []) {
  return ids.map((id) => getPlayerById(id)).filter(Boolean)
}

export function getComparables(player) {
  return getPlayersByIds(player?.topComparables || [])
}

export function getHistoricalMatches(playerId) {
  return [...(historicalComparisonMap[playerId] || [])]
    .map((match) => ({
      ...match,
      superScore: averageScores(match.comparisonScores),
    }))
    .sort((left, right) => right.superScore - left.superScore)
}

export function getHistoricalPlayerById(playerId) {
  return historicalPlayers.find((player) => player.id === playerId) || null
}

export function getDisplayPlayerById(playerId) {
  return getPlayerById(playerId) || getHistoricalPlayerById(playerId)
}