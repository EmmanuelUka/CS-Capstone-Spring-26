<script setup>
import { nextTick, onBeforeUnmount, ref, watch, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: null,
  },
  options: {
    type: Array,
    default: () => [],
  },
  placeholder: {
    type: String,
    default: 'Select option',
  },
  searchPlaceholder: {
    type: String,
    default: 'Search options',
  },
  emptyLabel: {
    type: String,
    default: 'No matches found.',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const rootRef = ref(null)
const searchInputRef = ref(null)
const isOpen = ref(false)
const query = ref('')

function normalizeValue(value) {
  return value == null ? '' : String(value)
}

const selectedOption = computed(
  () => props.options.find((option) => normalizeValue(option.value) === normalizeValue(props.modelValue)) || null
)

const filteredOptions = computed(() => {
  const normalizedQuery = query.value.trim().toLowerCase()

  if (!normalizedQuery) {
    return props.options
  }

  return props.options.filter((option) =>
    [option.label, option.description]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(normalizedQuery)
  )
})

function closeDropdown() {
  isOpen.value = false
  query.value = ''
}

async function toggleDropdown() {
  if (props.disabled) {
    return
  }

  isOpen.value = !isOpen.value

  if (isOpen.value) {
    await nextTick()
    searchInputRef.value?.focus()
  } else {
    query.value = ''
  }
}

function selectOption(option) {
  emit('update:modelValue', option.value)
  closeDropdown()
}

function handleDocumentPointerDown(event) {
  if (!rootRef.value?.contains(event.target)) {
    closeDropdown()
  }
}

watch(isOpen, (open) => {
  if (open) {
    document.addEventListener('pointerdown', handleDocumentPointerDown)
  } else {
    document.removeEventListener('pointerdown', handleDocumentPointerDown)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})
</script>

<template>
  <div ref="rootRef" class="searchable-dropdown" :class="{ open: isOpen, disabled }">
    <button
      class="dropdown-trigger"
      type="button"
      :disabled="disabled"
      @click="toggleDropdown"
    >
      <span class="trigger-copy">
        <strong>{{ selectedOption?.label || placeholder }}</strong>
        <small v-if="selectedOption?.description">{{ selectedOption.description }}</small>
      </span>
      <span class="trigger-icon">{{ isOpen ? '-' : '+' }}</span>
    </button>

    <div v-if="isOpen" class="dropdown-panel">
      <label class="search-field">
        <span class="sr-only">{{ searchPlaceholder }}</span>
        <input
          ref="searchInputRef"
          v-model="query"
          type="search"
          :placeholder="searchPlaceholder"
          @keydown.esc.prevent="closeDropdown"
        >
      </label>

      <div v-if="filteredOptions.length" class="option-list">
        <button
          v-for="option in filteredOptions"
          :key="`${normalizeValue(option.value)}-${option.label}`"
          class="option-button"
          :class="{ selected: normalizeValue(option.value) === normalizeValue(modelValue) }"
          type="button"
          @click="selectOption(option)"
        >
          <strong>{{ option.label }}</strong>
          <small v-if="option.description">{{ option.description }}</small>
        </button>
      </div>

      <p v-else class="empty-copy">{{ emptyLabel }}</p>
    </div>
  </div>
</template>

<style scoped>
.searchable-dropdown {
  position: relative;
}

.searchable-dropdown.open {
  z-index: 80;
}

.dropdown-trigger {
  width: 100%;
  min-height: 3rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.08), rgba(255, 255, 255, 0.02)),
    rgba(255, 255, 255, 0.04);
  color: #f2ece3;
  text-align: left;
  cursor: pointer;
}

.trigger-copy {
  display: grid;
  gap: 0.2rem;
}

.trigger-copy strong,
.option-button strong {
  font-size: 0.96rem;
}

.trigger-copy small,
.option-button small,
.empty-copy {
  color: rgba(242, 236, 227, 0.68);
}

.trigger-icon {
  position: absolute;
  top: 50%;
  right: 1rem;
  transform: translateY(-50%);
  font-size: 1.1rem;
  font-weight: 900;
  color: #ffcd7a;
}

.dropdown-panel {
  position: absolute;
  top: calc(100% + 0.45rem);
  left: 0;
  right: 0;
  z-index: 30;
  display: grid;
  gap: 0.75rem;
  padding: 0.85rem;
  border: 1px solid rgba(217, 151, 0, 0.22);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.12), rgba(255, 255, 255, 0.02)),
    rgba(10, 17, 31, 0.96);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.34);
  backdrop-filter: blur(20px);
}

.search-field input {
  width: 100%;
  min-height: 2.85rem;
  padding: 0.8rem 0.95rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  color: #f2ece3;
}

.option-list {
  display: grid;
  gap: 0.45rem;
  max-height: 16rem;
  overflow-y: auto;
}

.option-button {
  display: grid;
  gap: 0.2rem;
  width: 100%;
  padding: 0.8rem 0.9rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  color: #f2ece3;
  text-align: left;
  cursor: pointer;
}

.option-button.selected {
  outline: 1px solid rgba(217, 151, 0, 0.34);
  background:
    linear-gradient(180deg, rgba(217, 151, 0, 0.16), rgba(217, 151, 0, 0.05)),
    rgba(255, 255, 255, 0.04);
}

.empty-copy {
  margin: 0;
  padding: 0.35rem 0.1rem 0.1rem;
}

.disabled .dropdown-trigger {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
