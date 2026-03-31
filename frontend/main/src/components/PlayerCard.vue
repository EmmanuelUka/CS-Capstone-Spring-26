<template>
  <button
    class="player-card"
    type="button"
    :class="{ 'is-flipped': isFlipped }"
    @click="isFlipped = !isFlipped"
  >
    <span class="sr-only">
      {{ isFlipped ? 'Show front of card' : 'Show back of card' }}
    </span>

    <div class="card-face card-front">
      <div class="card-media" :style="frontBackgroundStyle">
        <div class="media-overlay" />
        <div v-if="!hasPhoto" class="media-placeholder">{{ initials }}</div>
      </div>

      <div class="front-topline">
        <div class="rating-cluster">
          <span class="rating-label">SuperScore</span>
          <span class="rating-value">{{ displayComparisonScore }}</span>
        </div>

        <span class="position-pill">{{ displayPrimaryRole }}</span>
      </div>

      <div class="front-bottom">
        <h2 class="player-name">{{ displayName }}</h2>

        <div class="front-measurements">
          <div class="measure-item">
            <span class="measure-label">Height</span>
            <strong>{{ displayHeight }}</strong>
          </div>
          <div class="measure-item">
            <span class="measure-label">Weight</span>
            <strong>{{ displayWeight }}</strong>
          </div>
        </div>
      </div>

      <section class="evaluation-strip front-evaluation">
        <div class="score-box">
          <span class="score-box-label">Scheme Fit</span>
          <strong>{{ displaySchemeFit }}</strong>
        </div>
        <div class="score-box">
          <span class="score-box-label">Confidence</span>
          <strong>{{ displayConfidence }}</strong>
        </div>
        <div class="score-box status-box">
          <span class="score-box-label">Status</span>
          <strong class="status-value">{{ displayStatus }}</strong>
        </div>
      </section>

    </div>

    <div class="card-face card-back">
      <div class="card-back-inner">
        <header class="back-header">
          <div>
            <p class="back-kicker">{{ displayPrimaryRole }}</p>
            <h3 class="back-name">{{ displayName }}</h3>
          </div>

          <div class="mini-score">
            <span>SuperScore</span>
            <strong>{{ displayComparisonScore }}</strong>
          </div>
        </header>

        <section class="back-section">
          <div class="section-heading">
            <span>Comparison Breakdown</span>
          </div>

          <div
            v-for="metric in breakdownItems"
            :key="metric.key"
            class="breakdown-row"
          >
            <div class="breakdown-copy">
              <span class="metric-name">{{ metric.label }}</span>
              <span class="metric-value">{{ metric.value }}</span>
            </div>
            <div class="metric-track">
              <span class="metric-fill" :style="{ width: metric.width }" />
            </div>
          </div>
        </section>

        <section class="back-section">
          <div class="section-heading">
            <span>Evaluations</span>
          </div>

          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">School</span>
              <span class="detail-value">{{ displaySchool }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Class</span>
              <span class="detail-value">{{ displayClass }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Competition</span>
              <span class="detail-value">{{ displayCompetitionLevel }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Games</span>
              <span class="detail-value">{{ displayGamesPlayed }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Recruit Type</span>
              <span class="detail-value">{{ displayRecruitType }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Listed Pos.</span>
              <span class="detail-value">{{ displayPosition }}</span>
            </div>
          </div>
        </section>

        <section class="back-section">
          <div class="section-heading">
            <span>AI Overview</span>
          </div>

          <div class="evaluation-row">
            <span class="eval-label">Coach Notes</span>
            <p class="eval-value">{{ displayNotes }}</p>
          </div>

          <div class="evaluation-row">
            <span class="eval-label">Synopsis</span>
            <p class="eval-value">{{ displaySynopsis }}</p>
          </div>

          <div v-if="displayInsufficientData" class="data-warning">
            Insufficient data for comparison
          </div>
        </section>
      </div>
    </div>
  </button>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  player: {
    type: Object,
    required: true,
  },
})

const fallback = 'N/A'

const displayName = computed(() => props.player?.name?.trim() || fallback)
const displaySchool = computed(() => props.player?.school?.trim() || 'Unknown School')
const displayClass = computed(() => props.player?.recruitingClass ?? fallback)
const displayHeight = computed(() => props.player?.ht?.trim() || fallback)
const displayWeight = computed(() => {
  const weight = props.player?.wt
  return weight || weight === 0 ? `${weight} lbs` : fallback
})
const displayPosition = computed(() => props.player?.position?.trim() || fallback)
const displayPrimaryRole = computed(
  () => props.player?.projectedPosition?.trim() || props.player?.position?.trim() || fallback
)
const displayCompetitionLevel = computed(
  () => props.player?.context?.competitionLevel?.trim() || fallback
)
const displayGamesPlayed = computed(() => props.player?.context?.gamesPlayed ?? fallback)
const displayRecruitType = computed(
  () => props.player?.context?.recruitType?.trim() || fallback
)
const displayComparisonScore = computed(
  () => formatPercentlessValue(props.player?.evaluation?.comparisonScore)
)
const displaySchemeFit = computed(() =>
  formatPercentValue(props.player?.evaluation?.schemeFitScore)
)
const displayConfidence = computed(() =>
  formatPercentValue(props.player?.evaluation?.confidenceScore)
)
const displayStatus = computed(
  () => props.player?.evaluation?.status?.trim() || 'Needs coach review'
)
const displayNotes = computed(
  () => props.player?.evaluation?.notes?.trim() || 'No notes yet'
)
const displaySynopsis = computed(
  () => props.player?.evaluation?.aiSynopsis?.trim() || 'No synopsis yet'
)
const displayInsufficientData = computed(
  () => Boolean(props.player?.evaluation?.insufficientData)
)
const photoUrl = computed(() => props.player?.photo?.trim() || '')
const hasPhoto = computed(() => Boolean(photoUrl.value))
const isFlipped = ref(false)

const initials = computed(() => {
  const name = props.player?.name?.trim()

  if (!name) {
    return 'NA'
  }

  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
})

const frontBackgroundStyle = computed(() => ({
  backgroundImage: photoUrl.value
    ? `linear-gradient(180deg, rgba(8, 15, 28, 0.04), rgba(8, 15, 28, 0.82)), url(${photoUrl.value})`
    : 'linear-gradient(180deg, rgba(255, 220, 129, 0.18), rgba(7, 12, 24, 0.92)), radial-gradient(circle at top, rgba(71, 85, 105, 0.95), rgba(15, 23, 42, 0.95))',
}))

const breakdownItems = computed(() => {
  const breakdown = props.player?.evaluation?.breakdown ?? {}

  return [
    { key: 'physical', label: 'Physical', rawValue: breakdown.physical, max: 25 },
    { key: 'athletic', label: 'Athletic', rawValue: breakdown.athletic, max: 25 },
    { key: 'production', label: 'Production', rawValue: breakdown.production, max: 35 },
    { key: 'context', label: 'Context', rawValue: breakdown.context, max: 15 },
  ].map((item) => ({
    ...item,
    value: formatScoreFraction(item.rawValue, item.max),
    width: normalizeWidth(item.rawValue, item.max),
  }))
})

function formatPercentValue(value) {
  return value || value === 0 ? `${value}%` : fallback
}

function formatPercentlessValue(value) {
  return value || value === 0 ? `${value}` : fallback
}

function formatScoreFraction(value, max) {
  return value || value === 0 ? `${value} / ${max}` : `N/A / ${max}`
}

function normalizeWidth(value, max) {
  if ((!value && value !== 0) || !max) {
    return '0%'
  }

  return `${Math.max(0, Math.min(100, (value / max) * 100))}%`
}
</script>

<style scoped>
.player-card {
  position: relative;
  box-sizing: border-box;
  overflow: hidden;
  display: block;
  width: 100%;
  max-width: 100%;
  margin-inline: auto;
  min-height: 35rem;
  transform-origin: center center;
  isolation: isolate;
  padding: 0;
  border: 1px solid rgba(255, 221, 153, 0.22);
  border-radius: 28px;
  background: transparent;
  box-shadow:
    0 20px 40px rgba(2, 8, 23, 0.46),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  color: #f8fafc;
  transition:
    transform 220ms ease,
    box-shadow 220ms ease,
    border-color 220ms ease;
  cursor: pointer;
  perspective: 1500px;
  transform-style: preserve-3d;
  text-align: left;
}

.player-card:hover {
  transform: translateY(-4px) scale(1.01);
  border-color: rgba(255, 221, 153, 0.45);
  box-shadow:
    0 28px 58px rgba(2, 8, 23, 0.58),
    0 0 28px rgba(245, 194, 66, 0.14);
}

.player-card:focus-visible {
  outline: 2px solid rgba(251, 191, 36, 0.8);
  outline-offset: 3px;
}

.player-card::before {
  position: absolute;
  content: '';
  inset: -25% -15% auto auto;
  width: 14rem;
  height: 14rem;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 231, 178, 0.22), transparent 68%);
  pointer-events: none;
}

.player-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
  pointer-events: none;
}

.card-face {
  position: absolute;
  box-sizing: border-box;
  inset: 0;
  left: 0;
  right: 0;
  display: grid;
  gap: 0.5rem;
  padding: 1.35rem;
  border-radius: inherit;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  transition: transform 0.7s ease;
  overflow: hidden;
  min-width: 0;
  width: 100%;
}

.card-front {
  grid-template-rows: 1fr auto;
  background:
    radial-gradient(circle at top, rgba(245, 194, 66, 0.18), transparent 32%),
    linear-gradient(160deg, #0f172a 0%, #172033 48%, #6d5319 100%);
}

.card-back {
  transform: rotateY(180deg);
  align-content: start;
  background:
    radial-gradient(circle at top, rgba(245, 194, 66, 0.16), transparent 28%),
    linear-gradient(180deg, #111827 0%, #172033 58%, #2f2411 100%);
  padding: 0;
  overflow-x: hidden;
  /* padding-right: 1rem; */
}

.card-back-inner {
  box-sizing: border-box;
  height: 100%;
  padding: .75rem;
  display: grid;
  gap: 1rem;
  overflow-y: auto;
  /* overflow-x: hidden; */
  scrollbar-width: none;
  scrollbar-color: transparent transparent;
  min-width: 0;
  width: 100%;
  margin: 0;
  align-items: stretch;
  justify-items: stretch;
}

.card-back-inner::-webkit-scrollbar {
  width: 0;
}

.player-card.is-flipped .card-front {
  transform: rotateY(180deg);
}

.player-card.is-flipped .card-back {
  transform: rotateY(0deg);
}

.card-media {
  position: absolute;
  inset: 0;
  background-position: center 40%;
  background-repeat: no-repeat;
  background-size: cover;
}

.media-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(8, 15, 28, 0.08) 0%, rgba(8, 15, 28, 0.55) 55%, rgba(8, 15, 28, 0.96) 100%),
    radial-gradient(circle at top, rgba(255, 212, 102, 0.18), transparent 32%);
}

.media-placeholder {
  position: absolute;
  left: 50%;
  top: 40%;
  display: grid;
  place-items: center;
  width: 8.4rem;
  height: 8.4rem;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  border: 2px solid rgba(255, 233, 184, 0.26);
  background: radial-gradient(circle at top, rgba(71, 85, 105, 0.88), rgba(15, 23, 42, 0.92));
  font-size: 2rem;
  font-weight: 900;
  color: rgba(255, 248, 235, 0.92);
  box-shadow:
    inset 0 1px 10px rgba(255, 255, 255, 0.08),
    0 14px 28px rgba(0, 0, 0, 0.28);
  opacity: 0.92;
}

.front-topline,
.back-header,
.section-heading,
.breakdown-copy,
.front-measurements,
.evaluation-strip,
.detail-grid {
  position: relative;
  z-index: 1;
}

.back-header,
.section-heading,
.back-section,
.evaluation-strip,
.detail-grid,
.breakdown-row,
.evaluation-row,
.metric-track {
  box-sizing: border-box;
  width: 100%;
}

.back-header {
  justify-content: space-between;
  align-items: flex-start;
}

.back-header > :first-child {
  min-width: 0;
  flex: 1 1 auto;
}

.mini-score {
  flex: 0 0 auto;
  justify-items: end;
  text-align: right;
}

.front-topline,
.back-header,
.breakdown-copy {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  min-width: 0;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  text-align: center;
}

.back-section {
  justify-items: stretch;
}

.front-topline {
  align-self: start;
}

.front-bottom {
  position: relative;
  z-index: 1;
  align-self: end;
  margin-bottom: 0;
}

.rating-cluster {
  display: grid;
  gap: 0.2rem;
}

.rating-label,
.measure-label,
.score-box-label,
.section-heading,
.metric-name,
.eval-label,
.detail-label,
.back-kicker,
.mini-score span {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 247, 237, 0.72);
}

.rating-value {
  font-size: clamp(2.6rem, 6vw, 4.2rem);
  font-weight: 900;
  line-height: 0.9;
  letter-spacing: -0.06em;
  color: #fbbf24;
  text-shadow: 0 6px 18px rgba(0, 0, 0, 0.34);
}

.position-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: center;
  width: fit-content;
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 233, 184, 0.3);
  background: rgba(255, 255, 255, 0.08);
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: center;
  max-width: 130px;
  white-space: normal;
  word-break: break-word;
  hyphens: auto;
  font-size: clamp(0.65rem, 1vw, 0.78rem);
}

.player-name,
.back-name {
  margin: 0;
  line-height: 1.03;
  font-weight: 900;
  color: #fff8eb;
}

.player-name {
  margin-bottom: 0.85rem;
  font-size: clamp(1.45rem, 3vw, 2rem);
  text-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
}

.back-name {
  font-size: 1.25rem;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.front-measurements {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

:where(.measure-item, .score-box, .detail-item) {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.6rem 0.75rem;
  min-height: 68px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(6px);
  text-align: center;
}

:where(.measure-item strong, .score-box strong, .detail-value, .mini-score strong) {
  color: #fff8eb;
  font-weight: 800;
  display: block;
  text-align: center;
  overflow-wrap: anywhere;
  word-break: break-word;
  hyphens: auto;
  line-height: 1.2;
}

:where(.measure-item strong, .detail-value, .mini-score strong) {
  font-size: clamp(1rem, 2vw, 1.15rem);
}

.score-box strong {
  font-size: clamp(0.95rem, 1.8vw, 1.15rem);
}

.score-box-label,
.measure-label,
.detail-label {
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 247, 237, 0.68);
}

.measure-item strong {
  font-size: 1.05rem;
}

.evaluation-strip,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(110px, 1fr));
  gap: 0.75rem;
}

.front-evaluation {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.front-evaluation .status-box {
  grid-column: 1 / -1;
}

.mini-score {
  display: grid;
  gap: 0.15rem;
  justify-items: end;
}

.section-heading {
  padding-bottom: 0.55rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.back-section {
  display: grid;
  gap: 0.75rem;
  padding: 0.95rem 1rem;
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.08);
  align-content: start;
}

.breakdown-row {
  display: grid;
  gap: 0.4rem;
  justify-items: stretch;
}

.metric-value {
  font-size: 0.88rem;
  font-weight: 700;
  color: #fff8eb;
  text-align: right;
  white-space: nowrap;
}

.metric-track,
.breakdown-row,
.evaluation-row {
  position: relative;
  z-index: 1;
}

.metric-track {
  overflow: hidden;
  height: 0.45rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.metric-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #fbbf24, #fef3c7);
}

.back-section .breakdown-row {
  background: rgba(255, 255, 255, 0.02);
  padding: 0.75rem;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.evaluation-row {
  display: grid;
  gap: 0.3rem;
  justify-items: stretch;
}

.eval-value {
  margin: 0;
  line-height: 1.5;
  color: rgba(255, 251, 235, 0.94);
}

.data-warning {
  padding: 0.8rem 0.9rem;
  border-radius: 14px;
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.22);
  color: #fecaca;
  font-size: 0.9rem;
  font-weight: 700;
}

.card-back-inner::-webkit-scrollbar {
  width: 8px;
}

.card-back-inner::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 999px;
}

.card-back-inner::-webkit-scrollbar-thumb {
  background: rgba(251, 191, 36, 0.45);
  border-radius: 999px;
}

.status-value {
  font-size: 0.84rem;
  line-height: 1.25;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 560px) {
  .player-card {
    min-height: 33rem;
  }

  .front-measurements,
  .evaluation-strip,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .card-face {
    padding: 1.15rem;
  }

  .card-back-inner {
    padding: 1.15rem;
  }

  .back-header,
  .breakdown-copy {
    gap: 0.5rem;
  }

  .back-name {
    font-size: 1.15rem;
  }

  .metric-name,
  .metric-value {
    font-size: 0.82rem;
  }

  .media-placeholder {
    width: 7.2rem;
    height: 7.2rem;
  }
}
</style>
