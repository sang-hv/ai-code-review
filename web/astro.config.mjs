import { defineConfig } from 'astro/config';

// NOTE: `site` and `base` are set for GitHub Pages project-page hosting
// (https://sang-hv.github.io/ai-code-review). Adjust or remove `base` if you
// deploy to a custom domain or the repo root.
export default defineConfig({
  site: 'https://sang-hv.github.io',
  base: '/ai-code-review',
});
