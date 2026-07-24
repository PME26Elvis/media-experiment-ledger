<script setup lang="ts">
interface Props {
  title: string
  subtitle: string
  icon: string
  color?: string
  to?: string
  value?: string
}
defineProps<Props>()
</script>
<template><v-hover v-slot="hover"><v-card v-bind="hover?.props" :to="to" class="glass module-card pa-5 h-100" :class="{ 'is-hovered': Boolean(hover?.isHovering) }"><div class="d-flex justify-space-between align-start"><v-avatar :color="color ?? 'primary'" variant="tonal" rounded="lg"><v-icon :icon="icon" /></v-avatar><v-icon v-if="to" icon="mdi-arrow-top-right" color="medium-emphasis" /></div><div v-if="value" class="metric-value mt-7">{{ value }}</div><h3 class="text-h6 font-weight-bold mt-5">{{ title }}</h3><p class="text-body-2 text-medium-emphasis mt-2 mb-0">{{ subtitle }}</p></v-card></v-hover></template>
