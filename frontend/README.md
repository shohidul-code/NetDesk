# NetDesk web app

React + TypeScript + Vite, React Router, TanStack Query, Tailwind CSS + shadcn/ui,
react-hook-form + zod. It talks only to the NetDesk API (`../docs/FRONTEND_AGENT_BRIEF.md`).

## Run

```bash
cp .env.example .env          # VITE_API_BASE_URL, the only setting
npm ci
npm run dev                   # http://localhost:5173; the API must allow it in CORS_ORIGINS
```

## Checks

```bash
npm run lint && npm run typecheck && npm test && npm run build
```

`npm test` runs Node's built-in test runner on `src/**/*.test.ts` (pure helpers only).

## API types

`src/api/schema.d.ts` is generated from the API's `/openapi.json`; never edit it by hand.
After an API change, with the API running:

```bash
npm run gen:api
```

## Notes

- `.npmrc` sets `min-release-age=7`: npm skips package versions younger than 7 days.
- TypeScript stays on 5.9 because `openapi-typescript` 7 does not support TypeScript 6+.
- The build output in `dist/` is a static site; the host must rewrite `/*` to `/index.html`.
