# Airbnb Guest Experience Intelligence Platform - Frontend

Next.js (App Router, TypeScript) SPA talking to the FastAPI backend in
`../app`. Auth is cookie-based (httpOnly JWTs set by the backend) - this
app never stores tokens itself; `credentials: "include"` on every request
is what carries the session.

## Getting started

**One-command option**: `docker compose up --build` from the repo root
starts the database, backend, and this app together (`:3000`). No local
Node/Python install needed. It's a production build, so it won't
hot-reload on file changes - use the steps below for active frontend
development instead.

**Local dev (hot-reload)**:

1. Backend must be running (`uvicorn app.main:app --reload` from the repo
   root) and reachable at the URL in `.env.local`
   (`NEXT_PUBLIC_API_BASE_URL`, defaults to `http://localhost:8000`).
2. Backend needs `CORS_ALLOWED_ORIGINS` to include this app's origin
   (`http://localhost:3000` by default - already set in the repo's
   `.env`).
3. `npm install`
4. `npm run dev` and open [http://localhost:3000](http://localhost:3000).

## Running inside docker-compose

`proxy.ts` calls the backend from the Next.js *server* process (not the
browser) to check `/auth/me` on every navigation. Inside docker-compose
that call needs the internal service hostname, which the browser can't
resolve - so there are two separate base-URL variables:

- `NEXT_PUBLIC_API_BASE_URL` - baked into the client bundle at build
  time; must be the URL the **browser** can reach (`http://localhost:8000`
  on the host, since the browser runs outside any container).
- `INTERNAL_API_BASE_URL` - read at runtime by `proxy.ts` only; the
  docker-compose service hostname (`http://app:8000`).

Both are wired up already in the root `docker-compose.yml`'s `web`
service - only relevant if you're changing how that's configured.

## One app, role-adaptive - not three portals

There are three distinct login entry points ("Guest Sign In",
"Host Sign In", and "Operations Sign In" - different copy/branding, all
call the same `POST /auth/login`), but everyone lands in the **same**
app at `/app/*` afterward. Role only controls which nav items and pages are visible/
reachable (see `components/app-shell/SidebarNav.tsx`'s `staffOnly`/
`hostOnly`/`guestOnly`/`manageOnly`/`trustSafetyOnly` group flags) -
there's no separate route tree or visual theme per role.

Seven roles in two tiers: **Guest**/**Host** are submitters, scoped to
their own feedback (plus guest-only property browsing/wishlist and
host-only property/performance dashboards). **Customer Support
Manager**/**Operations Manager**/**Product Manager**/**Trust &
Safety**/**Executive Leadership** are staff - all five can view every
case, analytics, and the weekly report; Support Manager and Ops Manager
can edit any case, bulk-upload, or export, and Trust & Safety can edit
the Safety-routed cases in their own bypass queue.

`proxy.ts` (Next.js 16 renamed `middleware.ts` to `proxy.ts`) gates
`/app/*` by forwarding the incoming cookie to `GET /auth/me` on every
navigation, and additionally redirects a user away from any role-gated
sub-path they can't use (`STAFF_ONLY_SEGMENTS`, `HOST_ONLY_SEGMENTS`,
`GUEST_ONLY_SEGMENTS`, `MANAGE_ONLY_SEGMENTS`,
`TRUST_SAFETY_ONLY_SEGMENTS`). This is a UX convenience, not the real
security boundary - every backend route independently enforces its own
auth/role checks, since a client-side redirect can always be bypassed by
calling the API directly.

## Structure

- `app/(public)/` - login, admin-login (operations sign-in), signup,
  forgot/reset password
- `app/app/` - the one authenticated app: feedback, profile, guest
  property browsing/wishlist, the host dashboard, the staff-only
  analytics/reports/operations/trust-safety pages
- `lib/` - API client, auth context, query client, formatting helpers
- `hooks/` - TanStack Query mutations/queries
- `components/ui/` - small hand-rolled primitives (Radix + Tailwind, no
  external component-library CLI dependency)
- `components/shared/`, `components/app-shell/`
