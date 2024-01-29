import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  docsSidebar: [
    'home',
    {
      'Tutorials': [
        {
          type: 'category',
          label: 'Getting started',
          link: {type: 'doc', id: 'tutorials/getting-started/index'},
          items: [
            'tutorials/getting-started/introduction-to-infrahub',
            'tutorials/getting-started/schema',
            'tutorials/getting-started/creating-an-object',
            'tutorials/getting-started/branches',
            'tutorials/getting-started/historical-data',
            'tutorials/getting-started/lineage-information',
            'tutorials/getting-started/git-integration',
            'tutorials/getting-started/jinja2-integration',
            'tutorials/getting-started/custom-api-endpoint',
            'tutorials/getting-started/graphql-query',
            'tutorials/getting-started/graphql-mutation'
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      link: {type: 'doc', id: 'guides/index'},
      items: [
        'guides/installation',
        'guides/schema',
        'guides/repository',
        'guides/jinja2-transform',
        'guides/python-transform',
        'guides/artifact',
      ],
    },
    {
      'Topics': [{type: 'autogenerated', dirName: 'topics'}],
    },
    {
      'Reference': [{type: 'autogenerated', dirName: 'reference'}],
    },
    {
      'Python SDK': [{type: 'autogenerated', dirName: 'python-sdk'}],
    },
    {
      'infrahubctl': [{type: 'autogenerated', dirName: 'infrahubctl'}],
    },
    {
      'Development': [{type: 'autogenerated', dirName: 'development'}],
    },
    {
      'Release Notes': [{type: 'autogenerated', dirName: 'release-notes'}],
    },
  ],
  nornirSidebar: [
    'nornir/index',
    {
      type: "html",
      value: '<span>Just custom HTML</span>',
    }
  ],
};

export default sidebars;
