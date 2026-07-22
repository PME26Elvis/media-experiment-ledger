import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import './styles.css'
import App from './App.vue'
import { vuetify } from './plugins/vuetify'
import { router } from './router'
import { i18n } from './i18n'

createApp(App).use(createPinia()).use(VueQueryPlugin).use(router).use(i18n).use(vuetify).mount('#app')
