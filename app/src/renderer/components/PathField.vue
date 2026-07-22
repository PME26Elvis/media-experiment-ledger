<script setup lang="ts">
const props = defineProps<{ modelValue:string; label:string; hint?:string }>()
const emit = defineEmits<{ 'update:modelValue':[value:string] }>()
async function browse(){ const value=await window.mel.chooseDirectory(props.modelValue || undefined); if(value) emit('update:modelValue',value) }
async function reveal(){ if(props.modelValue) await window.mel.revealPath(props.modelValue) }
</script>
<template><v-text-field :model-value="modelValue" :label="label" :hint="hint" persistent-hint prepend-inner-icon="mdi-folder-outline" @update:model-value="emit('update:modelValue', String($event))"><template #append-inner><v-btn icon="mdi-folder-search-outline" size="small" variant="text" color="primary" @click.stop="browse"/><v-btn icon="mdi-folder-open-outline" size="small" variant="text" color="secondary" :disabled="!modelValue" @click.stop="reveal"/></template></v-text-field></template>
