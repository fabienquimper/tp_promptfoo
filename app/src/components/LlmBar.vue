<template>
  <div class="d-flex align-center mr-1" style="gap: 6px">
    <!-- Statut de connexion -->
    <v-tooltip :text="statusLabel" location="bottom">
      <template #activator="{ props: tip }">
        <v-icon
          v-bind="tip"
          :icon="statusIcon"
          :color="statusColor"
          size="small"
          :aria-label="statusLabel"
        />
      </template>
    </v-tooltip>

    <!-- Modèle -->
    <v-chip
      v-if="settings?.llmModel"
      size="small"
      variant="tonal"
      color="white"
      prepend-icon="mdi-robot-outline"
      :aria-label="`Modèle : ${settings.llmModel}`"
    >
      {{ settings.llmModel }}
    </v-chip>

    <!-- URL (masquée sur mobile) -->
    <v-chip
      v-if="displayUrl"
      size="small"
      variant="tonal"
      color="white"
      prepend-icon="mdi-lan"
      class="d-none d-sm-flex"
      :aria-label="`Serveur : ${settings.llmBaseUrl}`"
    >
      {{ displayUrl }}
    </v-chip>

    <!-- Bouton de ping -->
    <v-btn
      icon="mdi-refresh"
      size="small"
      variant="text"
      aria-label="Tester la connexion LLM"
      @click="$emit('ping')"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  settings: { type: Object, default: () => ({}) },
  status: { type: String, default: 'unknown' },
})
defineEmits(['ping'])

const STATUS = {
  ok:      { icon: 'mdi-check-circle',  color: 'success', label: 'LLM connecté' },
  error:   { icon: 'mdi-alert-circle',  color: 'error',   label: 'LLM non accessible' },
  unknown: { icon: 'mdi-help-circle',   color: 'grey',    label: 'Connexion non vérifiée' },
}

const statusIcon  = computed(() => STATUS[props.status]?.icon  ?? STATUS.unknown.icon)
const statusColor = computed(() => STATUS[props.status]?.color ?? STATUS.unknown.color)
const statusLabel = computed(() => STATUS[props.status]?.label ?? STATUS.unknown.label)

const displayUrl = computed(() => {
  try {
    return new URL(props.settings?.llmBaseUrl ?? '').host
  } catch {
    return props.settings?.llmBaseUrl ?? ''
  }
})
</script>
