# Feedback Intelligence Platform - Frontend

Next.js (App Router, TypeScript) SPA talking to the FastAPI backend in
`../app`. Auth is cookie-based (httpOnly JWTs set by the backend) - this
app never stores tokens itself; `credentials: "include"` on every request
is what carries the session.

## Getting started

1. Backend must be running (`uvicorn app.main:app --reload` from the repo
   root, or `docker compose up`) and reachable at the URL in `.env.local`
   (`NEXT_PUBLIC_API_BASE_URL`, defaults to `http://localhost:8000`).
2. Backend needs `CORS_ALLOWED_ORIGINS` to include this app's origin
   (`http://localhost:3000` by default - already set in the repo's
   `.env`).
3. `npm install`
4. `npm run dev` and open [http://localhost:3000](http://localhost:3000).

## One app, role-adaptive - not two portals

There are two distinct login entry points ("Login to Give Feedback" and
"Admin Login" - different copy/branding, both call the same
`POST /auth/login`), but everyone lands in the **same** app at `/app/*`
afterward. Role only controls which nav items and pages are visible/
reachable (see `components/app-shell/AppSidebar.tsx`'s `adminOnly` group
flag) - there's no separate route tree or visual theme per role.

`proxy.ts` (Next.js 16 renamed `middleware.ts` to `proxy.ts`) gates
`/app/*` by forwarding the incoming cookie to `GET /auth/me` on every
navigation, and additionally redirects a non-admin away from the
admin-only sub-paths listed in `ADMIN_ONLY_SEGMENTS`. This is a UX
convenience, not the real security boundary - every backend route
independently enforces its own auth/role checks, since a client-side
redirect can always be bypassed by calling the API directly.

## Structure

- `app/(public)/` - login, admin-login, signup, forgot/reset password
- `app/app/` - the one authenticated app (feedback, profile, and the
  admin-only analytics/reports/administration pages)
- `lib/` - API client, auth context, query client, formatting helpers
- `hooks/` - TanStack Query mutations/queries
- `components/ui/` - small hand-rolled primitives (Radix + Tailwind, no
  external component-library CLI dependency)
- `components/shared/`, `components/app-shell/`
