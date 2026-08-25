import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";
import {
  canonicalErrorResponse,
  REQUEST_ID_HEADER,
} from "@/lib/server-errors";
import {
  ACCESS_COOKIE,
  clearAuthCookies,
  REFRESH_COOKIE,
  refreshBackendSession,
  requestIdFor,
  setAuthCookies,
  validateBffMutation,
} from "@/lib/server-auth";

const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const STRIPPED_REQUEST_HEADERS = [
  "authorization",
  "connection",
  "content-length",
  "cookie",
  "forwarded",
  "host",
  "origin",
  "proxy-authorization",
  "referer",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "x-csrf-token",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-port",
  "x-forwarded-proto",
  "x-real-ip",
];

function backendHeaders(request: NextRequest, accessToken?: string): Headers {
  const headers = new Headers(request.headers);
  for (const name of STRIPPED_REQUEST_HEADERS) headers.delete(name);
  headers.set(REQUEST_ID_HEADER, requestIdFor(request));
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return headers;
}

function proxyResponse(backendResponse: Response, apiUrl: string): NextResponse {
  const responseHeaders = new Headers(backendResponse.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("set-cookie");
  if (backendResponse.status >= 300 && backendResponse.status < 400) {
    const location = responseHeaders.get("location");
    if (location) {
      responseHeaders.set("location", location.replace(apiUrl, "/api/proxy"));
    }
  }
  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

async function proxyRequest(request: NextRequest) {
  if (MUTATION_METHODS.has(request.method)) {
    const rejection = validateBffMutation(request);
    if (rejection) return rejection;
  }

  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  const path = request.nextUrl.pathname.replace("/api/proxy", "");
  const search = request.nextUrl.search;
  const apiUrl = getBackendUrl();
  const url = `${apiUrl}${path}${search}`;

  try {
    const body =
      request.method !== "GET" && request.method !== "HEAD"
        ? await request.arrayBuffer()
        : null;
    const callBackend = (token?: string) =>
      fetch(
        new Request(url, {
          method: request.method,
          headers: backendHeaders(request, token),
          body: body ? body.slice(0) : null,
          redirect: "manual",
        }),
      );

    const firstResponse = await callBackend(accessToken);
    if (firstResponse.status !== 401 || !refreshToken) {
      return proxyResponse(firstResponse, apiUrl);
    }

    try {
      const refreshed = await refreshBackendSession(
        refreshToken,
        requestIdFor(request),
      );
      const retriedResponse = await callBackend(refreshed.access_token);
      const response = proxyResponse(retriedResponse, apiUrl);
      setAuthCookies(response, refreshed);
      return response;
    } catch {
      const response = proxyResponse(firstResponse, apiUrl);
      clearAuthCookies(response);
      return response;
    }
  } catch {
    const response = canonicalErrorResponse({
      request,
      status: 500,
      errorCode: "PROXY_ERROR",
    });
    console.error(
      `Proxy request failed request_id=${response.headers.get(REQUEST_ID_HEADER)}`,
    );
    return response;
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
