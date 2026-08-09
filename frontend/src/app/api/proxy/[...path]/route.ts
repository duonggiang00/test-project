import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";
import {
  canonicalErrorResponse,
  REQUEST_ID_HEADER,
} from "@/lib/server-errors";

async function proxyRequest(request: NextRequest) {
  // We use this route handler to proxy ALL requests to FastAPI.
  // We extract the HttpOnly cookie and append it as a Bearer token.
  
  const token = request.cookies.get("token")?.value;
  const path = request.nextUrl.pathname.replace("/api/proxy", "");
  const search = request.nextUrl.search;
  
  const apiUrl = getBackendUrl();
  const url = `${apiUrl}${path}${search}`;
  
  const headers = new Headers(request.headers);
  headers.delete("host"); // Let fetch set the host
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  try {
    const backendRequest = new Request(url, {
      method: request.method,
      headers: headers,
      body: request.method !== "GET" && request.method !== "HEAD" ? await request.arrayBuffer() : null,
      redirect: "manual",
    });
    
    const backendResponse = await fetch(backendRequest);
    
    // Copy the response
    const responseHeaders = new Headers(backendResponse.headers);
    responseHeaders.delete("content-encoding"); // Let Next.js handle it
    
    // Fix redirect leaks (e.g. trailing slash 307s from FastAPI)
    if (backendResponse.status >= 300 && backendResponse.status < 400) {
      const location = responseHeaders.get("location");
      if (location) {
        const newLocation = location.replace(apiUrl, "/api/proxy");
        responseHeaders.set("location", newLocation);
      }
    }
    
    return new NextResponse(backendResponse.body, {
      status: backendResponse.status,
      headers: responseHeaders,
    });
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
