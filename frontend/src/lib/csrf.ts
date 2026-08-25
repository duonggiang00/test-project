import { CSRF_COOKIE, CSRF_HEADER } from "@/lib/auth-contract";

let csrfRequest: Promise<string> | null = null;

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  const entry = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}

export async function ensureCsrfToken(): Promise<string> {
  const existing = readCookie(CSRF_COOKIE);
  if (existing) return existing;
  if (!csrfRequest) {
    csrfRequest = fetch("/api/auth/csrf", { method: "GET" })
      .then(async (response) => {
        const body = (await response.json()) as { csrf_token?: unknown };
        if (!response.ok || typeof body.csrf_token !== "string") {
          throw new Error("CSRF_BOOTSTRAP_FAILED");
        }
        return body.csrf_token;
      })
      .finally(() => {
        csrfRequest = null;
      });
  }
  return csrfRequest;
}

export async function csrfHeaders(): Promise<Record<string, string>> {
  return { [CSRF_HEADER]: await ensureCsrfToken() };
}
