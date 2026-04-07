import { createRouter, createWebHashHistory } from 'vue-router'

import DashboardView from '../views/DashboardView.vue'
import PlayerCardView from '../views/PlayerCardView.vue'
import PlayerComparisonView from '../views/PlayerComparisonView.vue'
import PlayerListView from '../views/PlayerListView.vue'
import ShortlistsView from '../views/ShortlistsView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/players', name: 'players', component: PlayerListView },
  {
    path: '/players/:playerId',
    name: 'player-card',
    component: PlayerCardView,
    props: true,
  },
  { path: '/compare', name: 'compare', component: PlayerComparisonView },
  { path: '/shortlists', name: 'shortlists', component: ShortlistsView },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
