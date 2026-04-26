<template>
  <v-dialog
    :model-value="modelValue"
    max-width="720"
    scrollable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card v-if="local">
      <v-card-title class="pt-4">
        Modifier le test {{ index + 1 }}
      </v-card-title>
      <v-card-subtitle class="pb-1 text-wrap">
        {{ local.description }}
      </v-card-subtitle>

      <v-divider />

      <v-card-text class="pa-4">
        <!-- Variables -->
        <p class="text-subtitle-2 mb-3">Variables</p>
        <div v-for="(_, key) in local.vars" :key="key" class="mb-3">
          <v-textarea
            v-model="local.vars[key]"
            :label="`vars.${key}`"
            variant="outlined"
            density="compact"
            auto-grow
            :rows="key === 'context' ? 8 : 2"
            :aria-label="`Variable ${key}`"
          />
        </div>

        <v-divider class="my-4" />

        <!-- Assertions -->
        <p class="text-subtitle-2 mb-3">Assertions</p>
        <v-row
          v-for="(a, i) in local.assert"
          :key="i"
          dense
          align="center"
          class="mb-2"
        >
          <v-col cols="4">
            <v-select
              v-model="a.type"
              :items="assertTypes"
              label="Type"
              variant="outlined"
              density="compact"
              hide-details
              :aria-label="`Type d'assertion ${i + 1}`"
            />
          </v-col>
          <v-col cols="8">
            <v-text-field
              v-model="a.value"
              label="Valeur attendue"
              variant="outlined"
              density="compact"
              hide-details
              :aria-label="`Valeur attendue pour l'assertion ${i + 1}`"
            />
          </v-col>
        </v-row>

        <!-- Ajouter une assertion -->
        <v-btn
          variant="text"
          size="small"
          prepend-icon="mdi-plus"
          class="mt-1"
          @click="addAssertion"
        >
          Ajouter une assertion
        </v-btn>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-3">
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">Annuler</v-btn>
        <v-btn color="primary" variant="flat" @click="save">Sauvegarder</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  test: { type: Object, default: null },
  index: { type: Number, default: 0 },
})
const emit = defineEmits(['update:modelValue', 'save'])

const local = ref(null)
const assertTypes = ['equals', 'icontains', 'contains']

watch(
  () => props.test,
  (t) => {
    if (t) local.value = JSON.parse(JSON.stringify(t))
  },
  { immediate: true },
)

function addAssertion() {
  if (!local.value.assert) local.value.assert = []
  local.value.assert.push({ type: 'equals', value: '' })
}

function save() {
  emit('save', props.index, local.value)
}
</script>
