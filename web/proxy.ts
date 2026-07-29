import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Next.js 16 renamed the `middleware.ts` file convention to `proxy.ts`
// (middleware is deprecated). See node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Role = "USER" | "ADMIN";
type Me = { role: Role } | null;

const ROLE_HOME: Record<Role, string> = {
  USER: "/portal",
  ADMIN: "/admin",
};

// Pages a logged-in visitor shouldn't see again - hitting one redirects
// them straight to their portal instead.
const AUTH_ENTRY_PAGES = new Set(["/login", "/admin-login", "/signup"]);

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
// a public auth page, not a protected one - tripping this into an
// unauthenticated-redirect-to-itself loop. Require a following "/" (or
// an exact match) so sibling routes like "/admin-login" don't count as
// "under" "/admin".
function isUnderSegment(pathname: string, segment: string): boolean {
  return pathname === segment || pathname.startsWith(`${segment}/`);
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const me = await fetchMe(request.headers.get("cookie"));

  if (pathname === "/") {
    return NextResponse.redirect(new URL(me ? ROLE_HOME[me.role] : "/login", request.url));
  }

  if (AUTH_ENTRY_PAGES.has(pathname) && me) {
    return NextResponse.redirect(new URL(ROLE_HOME[me.role], request.url));
  }

  if (isUnderSegment(pathname, "/portal")) {
    if (!me) return redirectToLogin(request, "/login");
    if (me.role !== "USER") return NextResponse.redirect(new URL(ROLE_HOME[me.role], request.url));
  }

  if (isUnderSegment(pathname, "/admin")) {
    if (!me) return redirectToLogin(request, "/admin-login");
    if (me.role !== "ADMIN") return NextResponse.redirect(new URL(ROLE_HOME[me.role], request.url));
  }

  return NextResponse.next();
}

function redirectToLogin(request: NextRequest, loginPath: string) {
  const url = new URL(loginPath, request.url);
  url.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/", "/login", "/admin-login", "/signup", "/portal/:path*", "/admin/:path*"],
};
