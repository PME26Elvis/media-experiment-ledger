import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { primaryPages } from './navigation.mjs';

export default defineConfig({
  site: 'https://pme26elvis.github.io',
  base: '/media-experiment-ledger',
  outDir: '../site',
  integrations: [
    starlight({
      title: 'Media Experiment Ledger',
      description: 'Release-backed analytics, system architecture, and machine-learning forecasts.',
      customCss: ['./src/styles/custom.css'],
      favicon: '/favicon.svg',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/PME26Elvis/media-experiment-ledger' }
      ],
      sidebar: [
        {
          label: 'Command Center',
          items: primaryPages.map(({ label, slug }) => ({ label, slug }))
        },
        {
          label: 'Reference',
          items: [
            { label: 'Forecast methodology', slug: 'forecast-methodology' },
            { label: 'Adding a new page', slug: 'extending-the-site' }
          ]
        }
      ],
      head: [
        { tag: 'meta', attrs: { name: 'theme-color', content: '#08111f' } },
        { tag: 'meta', attrs: { name: 'color-scheme', content: 'dark light' } }
      ]
    })
  ]
});
