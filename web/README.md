# ArgusReview — Web (landing + config builder)

Static Astro site: a landing page and a schema-driven `.ai-review.yaml`
config generator. It is **not** part of the Python package (excluded from the
PyPI build and the Docker image).

## Develop

```bash
pnpm install
pnpm dev            # http://localhost:4321/
```

## Config schema (single source of truth)

The builder reads `public/schema.json`, generated from the Python package so
the form never drifts from the actual config models:

```bash
# from the repo root, with the package installed (pip install .)
argus-review dump-schema -o web/public/schema.json
# or:  cd web && pnpm sync-schema
```

Regenerate it whenever `argus_review/libs/config/**` changes.

## Build

```bash
pnpm build          # outputs static site to web/dist/  (base = '/')
```

For hosting under a sub-path instead of the domain root:

```bash
PUBLIC_BASE_PATH=/some-path pnpm build
```

## Deploy to S3

The site is fully static — upload `dist/` to your bucket:

```bash
argus-review dump-schema -o public/schema.json   # keep schema fresh
pnpm build
aws s3 sync dist/ s3://<your-bucket>/ --delete
```

Bucket / CloudFront notes:
- Set the **index document** to `index.html`.
- The builder lives at `/config/` (served by `config/index.html`). With an S3
  *website* endpoint this works via index documents; behind CloudFront, add a
  rule so `/config/` resolves to `/config/index.html`.
- `schema.json` is served at the site root (`/schema.json`) — the builder
  fetches it relative to the base path.
