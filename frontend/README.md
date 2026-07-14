# SecureML Frontend

Enterprise-style frontend for the Secure & Compliant Machine Learning Security
Pipeline. React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui + React
Query + Recharts + Framer Motion.

## Run it

```bash
npm install
npm run dev
```

Open http://localhost:5173, sign in with the demo credentials shown on the
login page (`svc-ml-engineer` / `CHANGE_ME_IN_PRODUCTION`).

## Mock data vs. the real backend

By default (`VITE_USE_MOCKS=true`, the default even with no `.env`) every
page is powered by mock services in `src/services/*.ts`, which return data
grounded in this project's real generated reports (`src/data/real-facts.ts`)
rather than placeholder numbers.

To point the UI at the real FastAPI backend (Milestone 3, `app/main.py`)
instead:

1. Copy `.env.example` to `.env`.
2. Set `VITE_USE_MOCKS=false` and `VITE_API_URL` to wherever the API is
   running (e.g. `http://127.0.0.1:8000`, started via the repo root's
   `start.bat`).
3. Restart `npm run dev`.

Only `src/services/auth-service.ts` and `src/services/inference-service.ts`
currently call the real API when mocks are disabled (login and the Inference
API page's live demo) — every other page's service still reads static mock
data, since the backend doesn't yet expose endpoints for those modules
(dashboard summary, fairness metrics, drift status, etc.). Wiring those up is
a matter of replacing the `mockDelay(...)` call in each service file with a
real `apiClient.get(...)` call once those endpoints exist.

## Structure

```
src/
  app/            router
  components/
    ui/           shadcn primitives
    layout/       sidebar, topbar, shell, command palette, error boundary
    shared/       StatCard, StatusBadge, Section, PageHeader, etc.
  features/<name>/  one folder per sidebar page (page + local components)
  services/       mock/real data-fetching layer, one file per domain
  data/           real-facts.ts — ground-truth numbers from the project
  hooks/          auth context, theme context
  types/          shared TypeScript domain types
```

## Build

```bash
npm run build
```
