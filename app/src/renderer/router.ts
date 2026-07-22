import { createRouter, createWebHashHistory } from 'vue-router'
import AtlasView from './views/AtlasView.vue'
import AutomationView from './views/AutomationView.vue'
import DetectionView from './views/DetectionView.vue'
import ImportView from './views/ImportView.vue'
import JobsView from './views/JobsView.vue'
import ModelsView from './views/ModelsView.vue'
import ReportsView from './views/ReportsView.vue'
import SamplesView from './views/SamplesView.vue'
import SettingsView from './views/SettingsView.vue'
import UpdatesView from './views/UpdatesView.vue'
import WorkspaceView from './views/WorkspaceView.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/workspace' },
    { path: '/workspace', name: 'workspace', component: WorkspaceView },
    { path: '/import', name: 'import', component: ImportView },
    { path: '/samples', name: 'samples', component: SamplesView },
    { path: '/automation', name: 'automation', component: AutomationView },
    { path: '/atlas', name: 'atlas', component: AtlasView },
    { path: '/detection', name: 'detection', component: DetectionView },
    { path: '/jobs', name: 'jobs', component: JobsView },
    { path: '/models', name: 'models', component: ModelsView },
    { path: '/reports', name: 'reports', component: ReportsView },
    { path: '/updates', name: 'updates', component: UpdatesView },
    { path: '/settings', name: 'settings', component: SettingsView },
    { path: '/:pathMatch(.*)*', redirect: '/workspace' },
  ],
})
