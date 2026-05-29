<template>
  <v-container fluid class="pa-4">

    <!-- ── Barre d'outils ───────────────────────────────────────────────── -->
    <v-row align="center" class="mb-3">
      <v-col cols="12" sm="5" md="4">
        <v-select
          v-model="configFile"
          :items="configs"
          label="Jeu de tests"
          prepend-inner-icon="mdi-file-document-outline"
          variant="outlined"
          density="compact"
          hide-details
          aria-label="Sélectionner un fichier de configuration"
          @update:model-value="loadConfig"
        />
      </v-col>

      <v-col cols="auto">
        <v-text-field
          v-model.number="retries"
          type="number" min="0" max="10"
          label="Retries" suffix="×"
          variant="outlined" density="compact"
          hide-details style="width: 100px"
          :disabled="runningAll"
        />
      </v-col>

      <v-col cols="auto">
        <v-text-field
          v-model.number="retryDelaySec"
          type="number" min="1" max="120"
          label="Délai initial" suffix="s"
          variant="outlined" density="compact"
          hide-details style="width: 120px"
          :disabled="runningAll"
        />
      </v-col>

      <v-col cols="auto">
        <v-btn
          color="primary"
          prepend-icon="mdi-play-box-multiple-outline"
          :loading="runningAll"
          :disabled="!tests.length || runningAll"
          aria-label="Exécuter tous les tests"
          @click="runAll"
        >
          Tout exécuter
        </v-btn>
      </v-col>

      <v-col v-if="summary" cols="auto" class="d-flex align-center" style="gap: 6px">
        <v-chip color="success" size="small" prepend-icon="mdi-check">{{ summary.pass }}</v-chip>
        <v-chip color="error"   size="small" prepend-icon="mdi-close">{{ summary.fail }}</v-chip>
        <span class="text-caption text-medium-emphasis">/ {{ tests.length }}</span>
      </v-col>
    </v-row>

    <v-progress-linear
      v-if="runningAll"
      :model-value="progress"
      color="primary"
      height="4"
      rounded
      class="mb-3"
      :aria-label="`Progression : ${Math.round(progress)} %`"
    />

    <v-alert
      v-if="loadError"
      type="error"
      variant="tonal"
      closable
      class="mb-3"
      @click:close="loadError = null"
    >
      {{ loadError }}
    </v-alert>

    <!-- ── Tableau ───────────────────────────────────────────────────────── -->
    <v-data-table
      v-if="rows.length"
      v-model:expanded="expanded"
      :headers="headers"
      :items="rows"
      :loading="loading"
      item-value="idx"
      show-expand
      :items-per-page="25"
      :items-per-page-options="[10, 25, 50, -1]"
      :aria-label="`Tableau de ${tests.length} tests`"
      hover
      class="rounded border"
    >
      <!-- Groupe -->
      <template #item.group="{ item }">
        <v-chip :color="groupColor(item.group)" size="small" label>{{ item.group }}</v-chip>
      </template>

      <!-- Résultat attendu -->
      <template #item.assertValue="{ item }">
        <code class="text-caption">
          <span class="text-medium-emphasis mr-1">{{ assertLabel(item.assertType) }}</span>{{ truncate(item.assertValue, 35) }}
        </code>
      </template>

      <!-- Actions -->
      <template #item.actions="{ item }">
        <v-btn
          icon="mdi-pencil-outline"
          size="small"
          variant="text"
          :aria-label="`Modifier le test ${item.num}`"
          @click.stop="openEdit(item.idx)"
        />
        <v-btn
          icon="mdi-play-circle-outline"
          size="small"
          variant="text"
          color="primary"
          :loading="runningIndex === item.idx"
          :disabled="runningAll"
          :aria-label="`Exécuter le test ${item.num}`"
          @click.stop="runSingle(item.idx)"
        />
      </template>

      <!-- Résultat -->
      <template #item.result="{ item }">
        <template v-if="runningIndex === item.idx">
          <v-progress-circular indeterminate size="16" width="2" color="primary" aria-label="En cours…" />
        </template>
        <template v-else-if="results[item.idx] === undefined">
          <span class="text-disabled text-caption">—</span>
        </template>
        <template v-else-if="results[item.idx]?.error">
          <v-chip color="error" size="x-small" label>ERREUR</v-chip>
          <span class="text-caption text-error ml-1">{{ truncate(results[item.idx].error, 50) }}</span>
        </template>
        <template v-else>
          <div class="d-flex align-center flex-wrap" style="gap: 4px">
            <v-chip
              :color="results[item.idx].pass ? 'success' : 'error'"
              size="x-small"
              label
              :aria-label="results[item.idx].pass ? 'Test réussi' : 'Test échoué'"
            >
              {{ results[item.idx].pass ? 'PASS' : 'FAIL' }}
            </v-chip>
            <v-btn
              variant="text"
              size="x-small"
              density="compact"
              :aria-label="`Voir la réponse du test ${item.num}`"
              @click.stop="openOutput(item.idx)"
            >
              {{ truncate(results[item.idx].output, 50) }}
            </v-btn>
          </div>
        </template>
      </template>

      <!-- ── Ligne étendue ──────────────────────────────────────────────── -->
      <template #expanded-row="{ columns, item }">
        <tr>
          <td :colspan="columns.length" class="pa-0">
            <div class="expanded-panel pa-4">
              <v-row>

                <!-- Colonne gauche : prompt rendu -->
                <v-col cols="12" md="7">
                  <p class="text-subtitle-2 mb-2 d-flex align-center" style="gap: 6px">
                    <v-icon icon="mdi-text-box-outline" size="16" aria-hidden="true" />
                    Prompt envoyé au LLM
                  </p>
                  <pre class="expanded-pre">{{ renderPromptForTest(item.idx) }}</pre>
                </v-col>

                <!-- Colonne droite : variables + assertions -->
                <v-col cols="12" md="5">

                  <!-- Variables -->
                  <p class="text-subtitle-2 mb-2 d-flex align-center" style="gap: 6px">
                    <v-icon icon="mdi-variable" size="16" aria-hidden="true" />
                    Variables
                  </p>
                  <v-table density="compact" class="mb-3 rounded border">
                    <tbody>
                      <tr v-for="(val, key) in tests[item.idx]?.vars" :key="key">
                        <td class="text-caption font-weight-medium" style="width: 110px; vertical-align: top; padding-top: 8px">
                          {{ key }}
                        </td>
                        <td class="text-caption">
                          <template v-if="key === 'context'">
                            <span class="text-medium-emphasis">
                              {{ String(val).split('\n').length }} lignes
                            </span>
                            <v-btn
                              variant="text"
                              size="x-small"
                              class="ml-1"
                              @click="openContextDialog(item.idx)"
                              :aria-label="`Voir le contexte complet du test ${item.num}`"
                            >
                              Voir tout
                            </v-btn>
                          </template>
                          <template v-else>
                            <code>{{ val }}</code>
                          </template>
                        </td>
                      </tr>
                    </tbody>
                  </v-table>

                  <!-- Assertions -->
                  <p class="text-subtitle-2 mb-2 d-flex align-center" style="gap: 6px">
                    <v-icon icon="mdi-check-circle-outline" size="16" aria-hidden="true" />
                    Assertions
                  </p>
                  <div
                    v-for="(a, i) in tests[item.idx]?.assert"
                    :key="i"
                    class="d-flex align-center mb-1"
                    style="gap: 6px"
                  >
                    <v-chip size="x-small" variant="outlined">{{ assertLabel(a.type) }}</v-chip>
                    <code class="text-caption">{{ a.value }}</code>
                  </div>
                </v-col>

              </v-row>
            </div>
          </td>
        </tr>
      </template>
    </v-data-table>

    <!-- État vide -->
    <div v-else-if="!loading && !loadError" class="text-center pa-12 text-medium-emphasis">
      <v-icon icon="mdi-file-document-outline" size="48" class="mb-3" aria-hidden="true" />
      <p>Sélectionnez un fichier de configuration pour afficher les tests.</p>
    </div>

    <!-- ── Dialog : édition ──────────────────────────────────────────────── -->
    <EditDialog
      v-if="editIndex !== null"
      v-model="editDialogOpen"
      :test="tests[editIndex]"
      :index="editIndex"
      :prompt-template="promptTemplate"
      @save="saveTest"
    />

    <!-- ── Dialog : contexte complet ────────────────────────────────────── -->
    <v-dialog v-model="contextDialogOpen" max-width="640" scrollable>
      <v-card v-if="contextIndex !== null">
        <v-card-title class="pt-4">
          Contexte complet — Test {{ contextIndex + 1 }}
        </v-card-title>
        <v-divider />
        <v-card-text>
          <pre class="expanded-pre" style="max-height: 70vh">{{ tests[contextIndex]?.vars?.context }}</pre>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="contextDialogOpen = false">Fermer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ── Dialog : résultat d'exécution ────────────────────────────────── -->
    <v-dialog v-model="outputDialogOpen" max-width="860" scrollable>
      <v-card v-if="outputIndex !== null">
        <v-card-title class="d-flex align-center pt-4" style="gap: 8px">
          Test {{ outputIndex + 1 }}
          <v-chip :color="results[outputIndex]?.pass ? 'success' : 'error'" size="small">
            {{ results[outputIndex]?.pass ? 'PASS' : 'FAIL' }}
          </v-chip>
          <v-spacer />
          <v-chip
            v-if="results[outputIndex]?.usage"
            size="small"
            variant="tonal"
            prepend-icon="mdi-counter"
          >
            {{ results[outputIndex].usage.prompt_tokens }} + {{ results[outputIndex].usage.completion_tokens }} tokens
          </v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <div class="mb-4">
            <p class="text-subtitle-2 mb-2">Assertions</p>
            <v-chip
              v-for="(a, i) in results[outputIndex]?.assertions"
              :key="i"
              :color="a.pass ? 'success' : 'error'"
              size="small"
              variant="tonal"
              class="mr-1"
            >
              {{ assertLabel(a.type) }} {{ truncate(String(a.value), 40) }}
            </v-chip>
          </div>
          <v-expansion-panels variant="accordion" class="mb-4">
            <v-expansion-panel title="Prompt envoyé au LLM">
              <v-expansion-panel-text>
                <pre class="result-pre">{{ results[outputIndex]?.renderedPrompt }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
          <p class="text-subtitle-2 mb-2">Réponse du modèle</p>
          <pre class="result-pre">{{ results[outputIndex]?.output }}</pre>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="outputDialogOpen = false">Fermer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import EditDialog from './EditDialog.vue'

// ── état ──────────────────────────────────────────────────────────────────
const configs        = ref([])
const configFile     = ref('')
const tests          = ref([])
const promptTemplate = ref('')
const results        = ref({})
const loading        = ref(false)
const loadError      = ref(null)
const runningAll     = ref(false)
const runningIndex   = ref(null)
const progress       = ref(0)
const expanded       = ref([])

const retries        = ref(3)
const retryDelaySec  = ref(5)

const editDialogOpen    = ref(false)
const editIndex         = ref(null)
const outputDialogOpen  = ref(false)
const outputIndex       = ref(null)
const contextDialogOpen = ref(false)
const contextIndex      = ref(null)

// ── en-têtes ──────────────────────────────────────────────────────────────
const headers = [
  { title: '#',                key: 'num',         width: '55px' },
  { title: 'Groupe',           key: 'group',        width: '140px' },
  { title: 'Cible',            key: 'target',       width: '130px' },
  { title: 'Résultat attendu', key: 'assertValue',  minWidth: '180px' },
  { title: 'Actions',          key: 'actions',      width: '100px', sortable: false },
  { title: 'Résultat',         key: 'result',       sortable: false, minWidth: '220px' },
]

// ── données dérivées ──────────────────────────────────────────────────────
const rows = computed(() =>
  tests.value.map((t, i) => ({
    num:         i + 1,
    idx:         i,
    group:       extractGroup(t.description ?? ''),
    target:      extractTarget(t),
    assertType:  t.assert?.[0]?.type ?? '—',
    assertValue: String(t.assert?.[0]?.value ?? '—'),
    result:      null,
    actions:     null,
  }))
)

const summary = computed(() => {
  const r = Object.values(results.value)
  if (!r.length) return null
  return {
    pass: r.filter(x => x.pass && !x.error).length,
    fail: r.filter(x => !x.pass || x.error).length,
  }
})

// ── utilitaires ───────────────────────────────────────────────────────────
function extractGroup(description) {
  const m = description.match(/^\[([^\]]+)\]/)
  return m ? m[1] : '?'
}

function extractTarget(test) {
  if (test.vars?.target_item) return test.vars.target_item
  const m = (test.description ?? '').match(/—\s*(.+)$/)
  return m ? truncate(m[1], 22) : '—'
}

const GROUP_COLORS = { DÉBUT: 'blue', MILIEU: 'orange', FIN: 'deep-purple' }
function groupColor(group) {
  for (const [key, color] of Object.entries(GROUP_COLORS)) {
    if (group.startsWith(key)) return color
  }
  return 'grey'
}

const ASSERT_LABELS = { equals: '=', icontains: '⊃', contains: '∋' }
function assertLabel(type) { return ASSERT_LABELS[type] ?? type }

function truncate(str, n) {
  if (!str) return ''
  const s = String(str).replace(/\n/g, ' ').replace(/\s+/g, ' ').trim()
  return s.length > n ? s.slice(0, n) + '…' : s
}

function renderPromptForTest(idx) {
  const test = tests.value[idx]
  if (!test || !promptTemplate.value) return ''
  let result = promptTemplate.value
  for (const [key, value] of Object.entries(test.vars ?? {})) {
    result = result.replaceAll(`{{${key}}}`, String(value))
  }
  return result
}

// ── appels API ────────────────────────────────────────────────────────────
async function fetchConfigs() {
  try {
    const r = await fetch('/api/configs')
    configs.value = await r.json()
    if (configs.value.length) {
      configFile.value = configs.value[0]
      await loadConfig(configFile.value)
    }
  } catch (e) {
    loadError.value = e.message
  }
}

async function loadConfig(file) {
  if (!file) return
  loading.value = true
  loadError.value = null
  results.value = {}
  expanded.value = []
  try {
    const r = await fetch(`/api/config?file=${encodeURIComponent(file)}`)
    const data = await r.json()
    if (data.error) throw new Error(data.error)
    promptTemplate.value = data.config?.prompts?.[0]?.raw ?? ''
    tests.value = data.tests ?? []
  } catch (e) {
    loadError.value = e.message
    tests.value = []
  } finally {
    loading.value = false
  }
}

function retryParams() {
  return `retries=${retries.value}&retryDelayMs=${retryDelaySec.value * 1000}`
}

async function runSingle(idx) {
  runningIndex.value = idx
  try {
    const r = await fetch(`/api/run/${idx}?file=${encodeURIComponent(configFile.value)}&${retryParams()}`, { method: 'POST' })
    const data = await r.json()
    results.value = { ...results.value, [idx]: data }
  } catch (e) {
    results.value = { ...results.value, [idx]: { error: e.message, pass: false, output: '' } }
  } finally {
    runningIndex.value = null
  }
}

function runAll() {
  if (runningAll.value) return
  runningAll.value = true
  progress.value = 0
  results.value = {}

  const total = tests.value.length
  const es = new EventSource(`/api/run-all?file=${encodeURIComponent(configFile.value)}&${retryParams()}`)

  es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.done) { es.close(); runningAll.value = false; return }
    if (typeof data.index === 'number') {
      results.value = { ...results.value, [data.index]: data }
      progress.value = ((data.index + 1) / total) * 100
    }
  }
  es.onerror = () => { es.close(); runningAll.value = false }
}

function openEdit(idx) { editIndex.value = idx; editDialogOpen.value = true }
function openOutput(idx) { outputIndex.value = idx; outputDialogOpen.value = true }
function openContextDialog(idx) { contextIndex.value = idx; contextDialogOpen.value = true }

async function saveTest(idx, updatedTest) {
  try {
    const r = await fetch(`/api/config/test/${idx}?file=${encodeURIComponent(configFile.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedTest),
    })
    const data = await r.json()
    if (data.error) throw new Error(data.error)
    tests.value = tests.value.map((t, i) => i === idx ? updatedTest : t)
    editDialogOpen.value = false
  } catch (e) {
    console.error('Sauvegarde échouée :', e.message)
  }
}

onMounted(fetchConfigs)
</script>

<style scoped>
.expanded-panel {
  background: rgba(0, 0, 0, 0.02);
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.expanded-pre,
.result-pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: monospace;
  font-size: 12.5px;
  line-height: 1.55;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
  padding: 12px;
  overflow-y: auto;
}

.expanded-pre { max-height: 340px; }
.result-pre   { max-height: 50vh; }
</style>
