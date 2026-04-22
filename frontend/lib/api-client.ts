import { toast } from "sonner";
import { clearCredentials, getCredentials } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiOptions extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>;
}

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const creds = getCredentials();
  const headers: Record<string, string> = {
    ...(options.headers ?? {}),
  };

  if (creds) {
    headers["X-Tenant-ID"] = creds.tenantId;
    headers["X-API-Key"] = creds.apiKey;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearCredentials();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (res.status === 429) {
    const retryAfter = res.headers.get("Retry-After");
    const msg = retryAfter
      ? `Rate limit hit — retry in ${retryAfter}s`
      : "Rate limit hit — slow down";
    toast.error(msg);
    throw new Error("RateLimited");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // non-JSON body
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, opts?: ApiOptions) =>
    apiFetch<T>(path, { method: "GET", ...opts }),

  post: <T>(path: string, body?: unknown, opts?: ApiOptions) =>
    apiFetch<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
      ...opts,
    }),

  delete: <T>(path: string, opts?: ApiOptions) =>
    apiFetch<T>(path, { method: "DELETE", ...opts }),
};

export { API_URL };
