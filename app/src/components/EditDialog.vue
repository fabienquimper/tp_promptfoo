<template>
  <v-dialog
    :model-value="modelValue"
    max-width="820"
    scrollable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card v-if="local">
      <v-card-title class="pt-4">Modifier le test {{ index + 1 }}</v-card-title>
      <v-card-subtitle class="pb-1 text-wrap">{{ local.description }}</v-card-subtitle>

      <v-divider />

      <v-card-text class="pa-0">
        <v-tabs v-model="tab" color="primary" align-tabs="start">
          <v-tab value="vars">Variables</v-tab>
          <v-tab value="assert">Assertions</v-tab>
          <v-tab value="preview">Aperçu du prompt</v-tab>
        </v-tabs>

        <v-divider />

        <v-window v-model="tab" class="pa-4">

          <!-- ── Variables ──────────────────────────────────────────────── -->
          <v-window-item value="vars">
            <div v-for="(_, key) in local.vars" :key="key" class="mb-4">
              <v-textarea
                v-model="local.vars[key]"
                :label="`vars.${key}`"
                variant="outlined"
                density="compact"
                auto-grow
                :rows="key === 'context' ? 10 : 2"
                :aria-label="`Variable ${key}`"
              />
            </div>
          </v-window-item>

          <!-- ── Assertions ─────────────────────────────────────────────── -->
          <v-window-item value="assert">
            <v-row
              v-for="(a, i) in local.assert"
              :key="i"
              dense
              align="center"
              class="mb-3"
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
              <v-col cols="7">
                <v-text-field
                  v-model="a.value"
                  label="Valeur attendue"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :aria-label="`Valeur attendue pour l'assertion ${i + 1}`"
                />
              </v-col>
              <v-col cols="1" class="d-flex justify-center">
                <v-btn
                  icon="mdi-delete-outline"
                  size="small"
                  variant="text"
                  color="error"
                  :aria-label="`Supprimer l'assertion ${i + 1}`"
                  @click="local.assert.splice(i, 1)"
                />
              </v-col>
            </v-row>

            <v-btn
              variant="tonal"
              size="small"
              prepend-icon="mdi-plus"
              class="mt-1"
              @click="addAssertion"
            >
              Ajouter une assertion
            </v-btn>
          </v-window-item>

          <!-- ── Aperçu du prompt rendu ─────────────────────────────────── -->
          <v-window-item value="preview">
            <v-alert
              v-if="!promptTemplate"
              type="info"
              variant="tonal"
              density="compact"
              class="mb-3"
            >
              Template de prompt non disponible (rechargez le jeu de tests).
            </v-alert>
            <template v-else>
              <p class="text-caption text-medium-emphasis mb-3">
                Le prompt ci-dessous est mis à jour en temps réel au fil de vos modifications dans l'onglet Variables.
              </p>
              <pre class="prompt-pre">{{ renderedPrompt }}</pre>
            </template>
          </v-window-item>

        </v-window>
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
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue:     Boolean,
  test:           { type: Object, default: null },
  index:          { type: Number, default: 0 },
  promptTemplate: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'save'])

const local      = ref(null)
const tab        = ref('vars')
const assertTypes = ['equals', 'icontains', 'contains']

watch(
  () => props.test,
  (t) => { if (t) { local.value = JSON.parse(JSON.stringify(t)); tab.value = 'vars' } },
  { immediate: true },
)

const renderedPrompt = computed(() => {
  if (!props.promptTemplate || !local.value) return ''
  let result = props.promptTemplate
  for (const [key, value] of Object.entries(local.value.vars ?? {})) {
    result = result.replaceAll(`{{${key}}}`, String(value))
  }
  return result
})

function addAssertion() {
  if (!local.value.assert) local.value.assert = []
  local.value.assert.push({ type: 'equals', value: '' })
}

function save() { emit('save', props.index, local.value) }
</script>

<style scoped>
.prompt-pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: monospace;
  font-size: 12.5px;
  line-height: 1.55;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
  padding: 14px;
  max-height: 55vh;
  overflow-y: auto;
}
</style>
