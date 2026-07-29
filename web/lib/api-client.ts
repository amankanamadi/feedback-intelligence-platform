import { csrfHeader } from "@/lib/csrf";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : extractDetailMessage(detail));
    this.status = status;
    this.detail = detail;
  }
}

function extractDetailMessage(detail: unknown): string {
  if (detail && typeof detail === "object" && "detail" in detail) {
    const inner = (detail as { detail: unknown }).detail;
    if (typeof inner === "string") return inner;
    if (Array.isArray(inner) && inner.length > 0) {
      const first = inner[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  }
  return "Something went wrong. Please try again.";
}

async function safeJson(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

const MUTATING_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(MUTATING_METHODS.has(method) ? csrfHeader() : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    throw new ApiError(res.status, await safeJson(res));
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

export async function apiFetchForm<T>(path: string, formData: FormData, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "POST").toUpperCase();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method,
    credentials: "include",
    body: formData,
    headers: {
      ...(MUTATING_METHODS.has(method) ? csrfHeader() : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    throw new ApiError(res.status, await safeJson(res));
  }

  return (await res.json()) as T;
}
