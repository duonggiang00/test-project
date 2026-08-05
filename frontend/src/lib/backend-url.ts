const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

type BackendEnvironment = Record<string, string | undefined>;

export function getBackendUrl(
  environment: BackendEnvironment = process.env,
): string {
  const configuredUrl =
    environment.BACKEND_API_URL ||
    environment.NEXT_PUBLIC_API_URL ||
    DEFAULT_BACKEND_URL;
  const parsedUrl = new URL(configuredUrl);

  if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
    throw new Error("BACKEND_API_URL must use http or https");
  }
  if (parsedUrl.username || parsedUrl.password) {
    throw new Error("BACKEND_API_URL must not contain credentials");
  }
  if (
    parsedUrl.pathname !== "/" ||
    parsedUrl.search ||
    parsedUrl.hash
  ) {
    throw new Error("BACKEND_API_URL must be an origin without a path, query, or hash");
  }

  return parsedUrl.origin;
}
