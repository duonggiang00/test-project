import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getBackendUrl } from '@/lib/backend-url';

export async function POST(request: NextRequest) {
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
      },
      body: formData.toString(),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    // Set HttpOnly cookies
    const res = NextResponse.json({ user: data.user });
    
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
  } catch (error) {
    console.error("Login route error:", error);
    return NextResponse.json({ error_code: "INTERNAL_ERROR" }, { status: 500 });
  }
}
