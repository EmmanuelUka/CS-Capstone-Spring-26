export const homeMenuCards = [
  {
    id: 'playerCards',
    eyebrow: 'Live Module',
    title: 'Evaluation Cards',
    description:
      'Review athlete snapshots, comparison scoring, and coach-facing summaries in a presentation-ready card format.',
    badge: 'Ready now',
    actionLabel: 'Open board',
    icon: 'EC',
    accent: {
      from: '#ffbe72',
      to: '#ff7d54',
      shadow: 'rgba(255, 125, 84, 0.32)',
    },
    stats: [
      { label: 'Dataset', value: 'Test roster' },
      { label: 'Surface', value: 'Flip cards' },
    ],
  },
  {
    id: 'comingSoon',
    eyebrow: 'Next Module',
    title: 'Scouting Workflows',
    description:
      'Reserved space for the intake, watchlist, and recruiting workflow tools that should follow the home surface.',
    badge: 'Queued',
    actionLabel: 'Coming soon',
    icon: 'SW',
    disabled: true,
    accent: {
      from: '#99d7cb',
      to: '#4fae95',
      shadow: 'rgba(79, 174, 149, 0.24)',
    },
    stats: [
      { label: 'Status', value: 'Stubbed' },
      { label: 'Use case', value: 'Pipeline' },
    ],
  },
]
