<template>
  <v-app :theme="theme">
    <!-- Skip to main content (RGAA / accessibilité) -->
    <a href="#main-content" class="skip-link">Aller au contenu principal</a>

    <v-app-bar elevation="2" color="primary">
      <template #prepend>
        <v-icon icon="mdi-magnify" class="ml-3" aria-hidden="true" />
      </template>
      <v-app-bar-title>Promptfoo Runner</v-app-bar-title>

      <LlmBar :settings="llmSettings" :status="llmStatus" @ping="pingLLM" />

      <v-btn
        :icon="theme === 'light' ? 'mdi-weather-night' : 'mdi-white-balance-sunny'"
        :aria-label="theme === 'light' ? 'Activer le thème sombre' : 'Activer le thème clair'"
        @click="toggleTheme"
      />
    </v-app-bar>

    <v-main id="main-content">
      <TestRunner />
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LlmBar from './components/LlmBar.vue'
import TestRunner from './components/TestRunner.vue'

const theme = ref('light')
const llmSettings = ref({ llmBaseUrl: '', llmModel: '', hasApiKey: false })
const llmStatus = ref('unknown')

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
}

async function pingLLM() {
  llmStatus.value = 'unknown'
  try {
    const r = await fetch('/api/llm/ping')
    const data = await r.json()
    llmStatus.value = data.ok ? 'ok' : 'error'
  } catch {
    llmStatus.value = 'error'
  }
}

onMounted(async () => {
  try {
    const r = await fetch('/api/settings')
    llmSettings.value = await r.json()
  } catch {/* backend not yet ready */}
  pingLLM()
})
</script>

<style>
.skip-link {
  position: absolute;
  top: -100%;
  left: 0;
  z-index: 9999;
  padding: 8px 16px;
  background: #1565C0;
  color: #fff;
  font-size: 14px;
  text-decoration: none;
}
.skip-link:focus {
  top: 0;
}
</style>
