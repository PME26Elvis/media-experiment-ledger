<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'

const drawer = ref(true)
const rail = ref(false)
const { mdAndUp } = useDisplay()
const { t } = useI18n()
const route = useRoute()

watch(mdAndUp, (desktop) => {
  drawer.value = desktop
  if (!desktop) rail.value = false
}, { immediate: true })

const items = computed(() => [
  ['workspace', 'mdi-view-dashboard-outline'],
  ['import', 'mdi-folder-multiple-image'],
  ['samples', 'mdi-archive-eye-outline'],
  ['automation', 'mdi-robot-outline'],
  ['atlas', 'mdi-image-multiple-outline'],
  ['detection', 'mdi-vector-square'],
  ['jobs', 'mdi-progress-clock'],
  ['models', 'mdi-cube-outline'],
  ['reports', 'mdi-file-chart-outline'],
  ['integrations', 'mdi-connection'],
  ['updates', 'mdi-update'],
  ['diagnostics', 'mdi-shield-account-outline'],
  ['settings', 'mdi-cog-outline'],
].map(([name, icon]) => ({ name, icon, title: t(`nav.${name}`), to: `/${name}` })))
</script>

<template>
  <v-app>
    <v-app-bar v-if="!mdAndUp" color="surface" flat border="b">
      <v-app-bar-nav-icon :aria-label="t('common.menu')" @click="drawer = !drawer" />
      <v-app-bar-title>
        <span class="font-weight-bold">{{ t('app.name') }}</span>
      </v-app-bar-title>
    </v-app-bar>

    <v-navigation-drawer
      v-model="drawer"
      :rail="mdAndUp && rail"
      :permanent="mdAndUp"
      class="glass"
      width="292"
    >
      <div class="pa-4 d-flex align-center ga-3">
        <v-avatar color="primary" rounded="lg">
          <v-icon icon="mdi-flask-outline" />
        </v-avatar>
        <div v-if="!rail" class="min-width-0">
          <div class="font-weight-bold text-wrap">Media Experiment Ledger</div>
          <div class="text-caption text-medium-emphasis">Studio · Atlas · Detection · Automation</div>
        </div>
      </div>
      <v-divider class="mx-4 mb-2" />
      <v-list nav density="comfortable">
        <v-list-item
          v-for="item in items"
          :key="item.name"
          :to="item.to"
          :active="route.name === item.name"
          :prepend-icon="item.icon"
          :title="item.title"
          rounded="lg"
          color="primary"
          @click="!mdAndUp && (drawer = false)"
        />
      </v-list>
      <template v-if="mdAndUp" #append>
        <div class="pa-3">
          <v-btn
            block
            variant="text"
            :aria-label="rail ? t('common.expand') : t('common.compact')"
            :prepend-icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
            @click="rail = !rail"
          >
            {{ rail ? '' : t('common.compact') }}
          </v-btn>
        </div>
      </template>
    </v-navigation-drawer>

    <v-main>
      <router-view v-slot="{ Component }">
        <v-fade-transition mode="out-in">
          <component :is="Component" />
        </v-fade-transition>
      </router-view>
    </v-main>
  </v-app>
</template>
