<script setup lang="ts">
interface Props {
  eyebrow: string
  title: string
  subtitle: string
  icon: string
  color?: string
}
defineProps<Props>()
</script>
<template><div class="mb-8"><v-chip :color="color ?? 'primary'" variant="tonal" :prepend-icon="icon" class="mb-4">{{ eyebrow }}</v-chip><h1 class="page-title">{{ title }}</h1><p class="page-subtitle mt-4">{{ subtitle }}</p><slot /></div></template>
