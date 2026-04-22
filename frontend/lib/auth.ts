import type { Credentials } from "./types";

const KEY = "rag_credentials";

export function getCredentials(): Credentials | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Credentials) : null;
  } catch {
    return null;
  }
}

export function setCredentials(creds: Credentials): void {
  sessionStorage.setItem(KEY, JSON.stringify(creds));
}

export function clearCredentials(): void {
  sessionStorage.removeItem(KEY);
}
