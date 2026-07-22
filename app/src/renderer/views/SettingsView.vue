<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { StudioSettings } from '../../shared/contracts'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'
import SecretProfiles from '../components/SecretProfiles.vue'

const { locale } = useI18n()
const form = ref<StudioSettings>()
const saved = ref(false)

onMounted(async () => {
  form.value = await window.mel.settings.get()
  locale.value = form.value.locale
})

async function save() {
  if (!form.value) return
  form.value = await window.mel.settings.set(form.value)
  locale.value = form.value.locale
  saved.value = true
  setTimeout(() => { saved.value = false }, 1800)
}
</script>

<template>
  <div class="page-wrap">
    <PageHeader
      eyebrow="Preferences, paths & credentials"
      title="Settings"
      subtitle="Project paths remain explicit and browsable. Secrets use dedicated profiles and never enter ordinary project exports."
      icon="mdi-cog-outline"
    />
    <v-card v-if="form" class="glass pa-6">
      <v-row>
        <v-col cols="12" md="4">
          <v-select
            v-model="form.locale"
            label="Language"
            :items="[
              { title: '繁體中文', value: 'zh-TW' },
              { title: 'English', value: 'en' },
              { title: '简体中文', value: 'zh-CN' },
              { title: '日本語', value: 'ja' },
              { title: '한국어', value: 'ko' },
            ]"
            prepend-inner-icon="mdi-translate"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select v-model="form.appearance" label="Appearance" :items="['system', 'dark', 'light']" prepend-inner-icon="mdi-theme-light-dark" />
        </v-col>
        <v-col cols="12" md="4">
          <v-select v-model="form.closeBehavior" label="Close behavior" :items="['ask', 'tray', 'quit']" prepend-inner-icon="mdi-window-close" />
        </v-col>
        <v-col cols="12" md="6"><PathField v-model="form.imageInputPath" label="Default image input" /></v-col>
        <v-col cols="12" md="6"><PathField v-model="form.videoInputPath" label="Default video input" /></v-col>
        <v-col cols="12" md="6"><PathField v-model="form.atlasOutputPath" label="Default Atlas output" /></v-col>
        <v-col cols="12" md="6"><PathField v-model="form.detectionOutputPath" label="Default detection output" /></v-col>
        <v-col cols="12" md="6"><PathField v-model="form.generatedOutputPath" label="Default generated media output" /></v-col>
      </v-row>

      <v-divider class="my-5" />
      <div class="text-overline text-primary">Updates & interaction</div>
      <v-row>
        <v-col cols="12" md="4">
          <v-select
            v-model="form.updateChannel"
            label="Update channel"
            :items="[
              { title: 'Stable', value: 'stable' },
              { title: 'Beta', value: 'beta' },
              { title: 'Alpha', value: 'alpha' },
            ]"
            prepend-inner-icon="mdi-routes"
          />
        </v-col>
        <v-col cols="12" md="4"><v-switch v-model="form.checkUpdatesOnLaunch" color="primary" label="Check updates on launch" /></v-col>
        <v-col cols="12" md="4"><v-switch v-model="form.reducedMotion" color="primary" label="Reduce motion" /></v-col>
      </v-row>
      <v-alert variant="tonal" type="info" class="mb-5">
        Stable updates require signed release evidence. Linux uses verified manual packages; Windows and macOS use the automatic updater when packaged.
      </v-alert>
      <v-btn color="primary" prepend-icon="mdi-content-save-outline" @click="save">Save settings</v-btn>
      <v-snackbar v-model="saved" color="success">Settings saved</v-snackbar>
    </v-card>
    <SecretProfiles />
  </div>
</template>
