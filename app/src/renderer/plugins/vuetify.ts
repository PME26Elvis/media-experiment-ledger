import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

export const vuetify = createVuetify({
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  theme: {
    defaultTheme: 'studioDark',
    themes: {
      studioDark: { dark: true, colors: { background: '#080d1a', surface: '#10182a', 'surface-bright': '#1a2942', primary: '#7c8cff', secondary: '#41d6c3', accent: '#ffb86b', success: '#4ade80', warning: '#fbbf24', error: '#fb7185', info: '#38bdf8' } },
      studioLight: { dark: false, colors: { background: '#f4f7fb', surface: '#ffffff', 'surface-bright': '#edf2fa', primary: '#5265e8', secondary: '#008f82', accent: '#d97706', success: '#15803d', warning: '#b45309', error: '#be123c', info: '#0369a1' } },
    },
  },
  defaults: {
    VBtn: { rounded: 'lg', elevation: 0 },
    VCard: { rounded: 'xl', elevation: 0 },
    VTextField: { variant: 'outlined', density: 'comfortable', color: 'primary' },
    VSelect: { variant: 'outlined', density: 'comfortable', color: 'primary' },
  },
})
