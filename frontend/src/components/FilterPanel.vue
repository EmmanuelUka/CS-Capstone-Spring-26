<script setup>
defineProps({
  filters: {
    type: Object,
    required: true,
  },
  options: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:filters'])

function setFilter(key, value, filters) {
  emit('update:filters', {
    ...filters,
    [key]: value,
  })
}

function clearFilters(filters) {
  emit('update:filters', {
    ...filters,
    query: '',
    position: 'All',
    state: 'All',
    type: 'All',
    ratingFloor: 0,
  })
}
</script>

<template>
  <section class="filter-panel">
    <div class="filter-header">
      <div>
        <p class="filter-label">Player Filters</p>
        <h3>Search and narrow the board</h3>
      </div>

      <button class="ghost-button pill-button" type="button" @click="clearFilters(filters)">
        Reset
      </button>
    </div>

    <div class="filter-grid">
      <label class="field">
        <span>Search</span>
        <input
          :value="filters.query"
          type="search"
          placeholder="Name, school, city"
          @input="setFilter('query', $event.target.value, filters)"
        >
      </label>

      <label class="field">
        <span>Position</span>
        <select :value="filters.position" @change="setFilter('position', $event.target.value, filters)">
          <option v-for="option in options.positions" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>

      <label class="field">
        <span>State</span>
        <select :value="filters.state" @change="setFilter('state', $event.target.value, filters)">
          <option v-for="option in options.states" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>

      <label class="field">
        <span>Type</span>
        <select
          :value="filters.type"
          @change="setFilter('type', $event.target.value, filters)"
        >
          <option v-for="option in options.types" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
    </div>

    <label class="range-field">
      <div class="range-copy">
        <span>Minimum Rating</span>
        <strong>{{ filters.ratingFloor }}</strong>
      </div>
      <input
        :value="filters.ratingFloor"
        type="range"
        min="0"
        max="100"
        step="1"
        @input="setFilter('ratingFloor', Number($event.target.value), filters)"
      >
    </label>
  </section>
</template>

<style scoped>
.filter-panel {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(25, 22, 29, 0.82);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}

.filter-label,
.field span,
.range-copy span {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(242, 236, 227, 0.5);
}

.filter-header h3 {
  margin: 0.25rem 0 0;
  font-size: 1.1rem;
}

.filter-grid {
  display: grid;
  gap: 0.85rem;
}

.field {
  display: grid;
  gap: 0.45rem;
}

.field input,
.field select,
.range-field input {
  width: 100%;
}

.field input,
.field select {
  padding: 0.88rem 0.95rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  color: #f2ece3;
}

.field select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background:
    linear-gradient(45deg, transparent 50%, rgba(242, 236, 227, 0.7) 50%),
    linear-gradient(135deg, rgba(242, 236, 227, 0.7) 50%, transparent 50%),
    rgba(255, 255, 255, 0.04);
  background-position:
    calc(100% - 1.1rem) calc(50% - 0.12rem),
    calc(100% - 0.8rem) calc(50% - 0.12rem),
    0 0;
  background-size:
    0.38rem 0.38rem,
    0.38rem 0.38rem,
    100% 100%;
  background-repeat: no-repeat;
  padding-right: 2.2rem;
}

.field select option {
  background: #211c1f;
  color: #f2ece3;
}

.range-field {
  display: grid;
  gap: 0.7rem;
}

.range-copy {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.range-copy strong {
  font-size: 1rem;
}

.pill-button {
  padding: 0.7rem 0.95rem;
  border-radius: 999px;
}

@media (min-width: 720px) {
  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
