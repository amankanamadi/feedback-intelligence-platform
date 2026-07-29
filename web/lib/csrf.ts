// Double-submit CSRF cookie support - a no-op today. SameSite=Lax on the
// access-token cookie plus the backend's explicit CORS origin allowlist
// (allow_credentials without a wildcard origin) is the primary CSRF
// defense already in place. If the backend later issues a non-httpOnly
// `csrf_token` cookie, this starts echoing it as a header automatically -
// deliberately not hard-failing in the meantime.
const CSRF_COOKIE_NAME = "csrf_token";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function csrfHeader(): Record<string, string> {
  const token = readCookie(CSRF_COOKIE_NAME);
  return token ? { "X-CSRF-Token": token } : {};
}
