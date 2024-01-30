import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLinksValidator from 'starlight-links-validator'

// https://astro.build/config
export default defineConfig({
  server: {
    headers: {
      "Access-Control-Allow-Origin": "*"
    }
  },
	integrations: [
		starlight({
      // plugins: [
      //   starlightLinksValidator({
      //     errorOnFallbackPages: false,
      //     errorOnInconsistentLocale: false,
      //     errorOnRelativeLinks: false,
      //   })
      // ],
      components: {
        Header: './src/components/Header.astro'
      },
      favicon: '/favicon.ico',
			title: 'Docs',
      logo: {
        src: './src/assets/infrahub.svg',
        replacesTitle: true,
      },
      customCss: [
        './src/fonts/font-face.css',
      ],
      editLink: {
        baseUrl: 'https://github.com/opsmill/infrahub/tree/bab-docusaurus-demo/docs-starlight/',
      },
			social: {
				github: 'https://github.com/opsmill/infrahub',
			},
			sidebar: [
				{
					label: 'Tutorials',
          collapsed: true,
          items: [
            {
              label: 'Getting started',
              badge: { text: 'Hot'  },
              autogenerate: { directory: 'tutorials/getting-started' },
            },
          ]
				},
				{
					label: 'Guides',
          collapsed: true,
          autogenerate: { directory: 'guides' },
				},
        {
          label: 'Topics',
          collapsed: true,
          autogenerate: { directory: 'topics' },
        },
        {
          label: 'Reference',
          collapsed: true,
          autogenerate: { directory: 'reference' },
        },
        {
          label: 'Python SDK',
          collapsed: true,
          autogenerate: { directory: 'python-sdk' },
        },
        {
          label: 'infrahubctl',
          collapsed: true,
          autogenerate: { directory: 'infrahubctl' },
        },
				{
					label: 'Development',
          collapsed: true,
          badge: { text: 'WIP', variant: 'caution' },
					autogenerate: { directory: 'development' },
				},
        {
					label: 'Release Notes',
          collapsed: false,
					autogenerate: { directory: 'release-notes' },
				},
			],
		}),
	],
});
