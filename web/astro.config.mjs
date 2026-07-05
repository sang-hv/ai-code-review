import { defineConfig } from 'astro/config';

// `base` defaults to '/' which suits an S3 bucket / CloudFront served at the
// root. For hosting under a sub-path (e.g. GitHub Pages project page), set
// PUBLIC_BASE_PATH, e.g. PUBLIC_BASE_PATH=/argus-code-review pnpm build.
const base = process.env.PUBLIC_BASE_PATH || '/';

export default defineConfig({
  base,
});
