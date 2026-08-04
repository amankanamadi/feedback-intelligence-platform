import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Next.js 16 renamed the `middleware.ts` file convention to `proxy.ts`
// (middleware is deprecated). See node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md.

// proxy.ts runs server-side (inside the Next.js process, not the
// browser) - in docker-compose that means it must reach the backend via
// the internal service hostname (INTERNAL_API_BASE_URL=http://app:8000),
// never the browser-facing NEXT_PUBLIC_ one. Local dev sets neither, so
// it falls through to the same localhost default as before.
const API_BASE_URL =
  process.env.INTERNAL_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Role = "GUEST" | "HOST" | "SUPPORT_MANAGER" | "OPS_MANAGER" | "PRODUCT_MANAGER" | "TRUST_SAFETY" | "EXEC";
type Me = { role: Role } | null;

const STAFF_ROLES = new Set<Role>(["SUPPORT_MANAGER", "OPS_MANAGER", "PRODUCT_MANAGER", "TRUST_SAFETY", "EXEC"]);

// Both login entry points ("Login to Give Feedback" and "Operations Login")
// land here regardless of role - one app, not two portals.
const APP_HOME = "/app";

// Pages a logged-in visitor shouldn't see again - hitting one redirects
// them straight into the app instead.
const AUTH_ENTRY_PAGES = new Set(["/login", "/admin-login", "/signup"]);

// Sub-paths under /app that only render/apply for staff (Support Manager,
// Ops Manager, Product Manager, Exec Leadership) - a Guest/Host hitting
// one directly by URL is bounced back to /app. Defense-in-depth on top of
// the backend's own 403s and the sidebar simply not rendering the link
// for a submitter-role user.
const STAFF_ONLY_SEGMENTS = [
  "/app/analytics",
  "/app/reports",
  "/app/users",
  "/app/categories",
  "/app/ai-config",
  "/app/settings",
  "/app/audit-logs",
];

// Same defense-in-depth rationale as STAFF_ONLY_SEGMENTS, for the one
// host-only page.
const HOST_ONLY_SEGMENTS = ["/app/host"];

// Same rationale, for the one guest-only page. /app/properties is
// deliberately NOT in any of these arrays - browsing listings is open to
// every role, matching GET /properties's own design.
const GUEST_ONLY_SEGMENTS = ["/app/wishlist"];

async function fetchMe(cookieHeader: string | null): Promise<Me> {
  if (!cookieHeader) return null;
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as Me;
  } catch {
    // Backend unreachable - fail closed on protected routes (handled by
    // the caller treating `null` as unauthenticated), fail open on public
    // auth pages (no redirect away, so it's a benign no-op there).
    return null;
  }
}

// Plain `pathname.startsWith("/admin")` would also match "/admin-login" -
// a public auth page, not a protected one. Require a following "/" (or
// an exact match) so sibling routes don't count as "under" a segment.
function isUnderSegment(pathname: string, segment: string): boolean {
  return pathname === segment || pathname.startsWith(`${segment}/`);
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const me = await fetchMe(request.headers.get("cookie"));

  if (pathname === "/") {
    return NextResponse.redirect(new URL(me ? APP_HOME : "/login", request.url));
  }

  if (AUTH_ENTRY_PAGES.has(pathname) && me) {
    return NextResponse.redirect(new URL(APP_HOME, request.url));
  }

  if (isUnderSegment(pathname, "/app")) {
    if (!me) return redirectToLogin(request);
    if (STAFF_ONLY_SEGMENTS.some((segment) => isUnderSegment(pathname, segment)) && !STAFF_ROLES.has(me.role)) {
      return NextResponse.redirect(new URL(APP_HOME, request.url));
    }
    if (HOST_ONLY_SEGMENTS.some((segment) => isUnderSegment(pathname, segment)) && me.role !== "HOST") {
      return NextResponse.redirect(new URL(APP_HOME, request.url));
    }
    if (GUEST_ONLY_SEGMENTS.some((segment) => isUnderSegment(pathname, segment)) && me.role !== "GUEST") {
      return NextResponse.redirect(new URL(APP_HOME, request.url));
    }
  }

  return NextResponse.next();
}

function redirectToLogin(request: NextRequest) {
  const url = new URL("/login", request.url);
  url.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/", "/login", "/admin-login", "/signup", "/app/:path*"],
};
