import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getBackendUrl } from '@/lib/backend-url';
import {
  canonicalErrorResponse,
  canonicalizeRequestId,
  forwardBackendError,
  getOrCreateRequestId,
  REQUEST_ID_HEADER,
} from '@/lib/server-errors';

export async function POST(request: NextRequest) {
  const requestId = getOrCreateRequestId(request);
  try {
    const body = await request.json();
    const { email, password, rememberMe } = body;

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const apiUrl = getBackendUrl();
    
    const response = await fetch(`${apiUrl}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        [REQUEST_ID_HEADER]: requestId,
      },
      body: formData.toString(),
    });

    const data = await response.json();

    if (!response.ok) {
      return forwardBackendError(request, response, data, requestId);
    }

    // Set HttpOnly cookies
    const res = NextResponse.json({ user: data.user });
    const backendRequestId = canonicalizeRequestId(
      response.headers.get(REQUEST_ID_HEADER),
    ) ?? requestId;
    res.headers.set(REQUEST_ID_HEADER, backendRequestId);
    
    // 7 days if rememberMe is true, otherwise session cookie (no maxAge)
    const cookieOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      path: "/",
      ...(rememberMe ? { maxAge: 60 * 60 * 24 * 7 } : {})
    };

    res.cookies.set({
      name: "token",
      value: data.access_token,
      ...cookieOptions,
    });
    
    res.cookies.set({
      name: "role",
      value: data.user.role,
      httpOnly: false, // role needs to be read by client-side if needed
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      path: "/",
      ...(rememberMe ? { maxAge: 60 * 60 * 24 * 7 } : {})
    });

    return res;
  } catch {
    const response = canonicalErrorResponse({
      request,
      status: 500,
      errorCode: "INTERNAL_ERROR",
      upstreamRequestId: requestId,
    });
    console.error(
      `Login route failed request_id=${response.headers.get(REQUEST_ID_HEADER)}`,
    );
    return response;
  }
}
