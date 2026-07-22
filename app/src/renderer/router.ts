import { createRouter, createWebHashHistory } from 'vue-router'
import WorkspaceView from './views/WorkspaceView.vue'
import ImportView from './views/ImportView.vue'
import AutomationView from './views/AutomationView.vue'
import AtlasView from './views/AtlasView.vue'
import DetectionView from './views/DetectionView.vue'
import JobsView from './views/JobsView.vue'
import SettingsView from './views/SettingsView.vue'
import GenericView from './views/GenericView.vue'

export const router = createRouter({ history: createWebHashHistory(), routes: [
  { path: '/', redirect: '/workspace' },
  { path: '/workspace', name: 'workspace', component: WorkspaceView },
  { path: '/import', name: 'import', component: ImportView },
  { path: '/automation', name: 'automation', component: AutomationView },
  { path: '/atlas', name: 'atlas', component: AtlasView },
  { path: '/detection', name: 'detection', component: DetectionView },
  { path: '/jobs', name: 'jobs', component: JobsView },
  { path: '/models', name: 'models', component: GenericView, props: { module: 'models' } },
  { path: '/reports', name: 'reports', component: GenericView, props: { module: 'reports' } },
  { path: '/updates', name: 'updates', component: GenericView, props: { module: 'updates' } },
  { path: '/settings', name: 'settings', component: SettingsView },
] })
