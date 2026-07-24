<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'; import type { JobRecord } from '../../shared/contracts'; import PageHeader from '../components/PageHeader.vue'; import JobCard from '../components/JobCard.vue'
const jobs=ref<JobRecord[]>([]); let timer:number|undefined
async function refresh(){ jobs.value=await window.mel.jobs.list() }
async function control(id:string,action:'pause'|'resume'|'cancel'){ await window.mel.jobs.control(id,action); await refresh() }
onMounted(()=>{ void refresh(); timer=window.setInterval(refresh,1500) }); onBeforeUnmount(()=>timer&&clearInterval(timer))
</script>
<template><div class="page-wrap"><PageHeader eyebrow="Durable jobs" title="Job Center" subtitle="Every nontrivial operation has an identity, state machine, item progress, recovery path and final verification stage." icon="mdi-progress-clock"/><v-row v-if="jobs.length"><v-col v-for="job in jobs" :key="job.id" cols="12" lg="6"><JobCard :job="job" @control="control"/></v-col></v-row><v-card v-else class="glass pa-10 text-center"><v-icon icon="mdi-check-circle-outline" color="success" size="64"/><div class="text-h5 mt-4">No jobs yet</div><div class="text-medium-emphasis">Create work from Import, Automation, Atlas or Detection Studio.</div></v-card></div></template>
