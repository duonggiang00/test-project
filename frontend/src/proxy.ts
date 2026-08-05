import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  const role = request.cookies.get('role')?.value;
  const path = request.nextUrl.pathname;

  // Protect /admin routes
  if (path.startsWith('/dashboard') || path.startsWith('/materials') || path.startsWith('/topics') || path.startsWith('/history') || path.startsWith('/students')) {
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    if (role === 'student') {
      return NextResponse.redirect(new URL('/student/home', request.url));
    }
  }

  // Protect /student routes
  if (path.startsWith('/student')) {
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    if (role !== 'student') {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }

  // Prevent logged-in users from visiting auth pages
  if (path === '/login' || path === '/register' || path === '/') {
    if (token) {
      if (role === 'student') {
        return NextResponse.redirect(new URL('/student/home', request.url));
      } else {
        return NextResponse.redirect(new URL('/dashboard', request.url));
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
