import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const hasSession = Boolean(
    request.cookies.get('access_token')?.value ||
    request.cookies.get('refresh_token')?.value,
  );
  const path = request.nextUrl.pathname;

  // Protect /admin routes
  if (
    [
      '/dashboard',
      '/materials',
      '/topics',
      '/history',
      '/students',
      '/exams',
      '/questions',
      '/ai-workspace',
      '/reports',
    ].some((prefix) => path.startsWith(prefix))
  ) {
    if (!hasSession) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  // Protect /student routes
  if (path.startsWith('/student')) {
    if (!hasSession) {
      return NextResponse.redirect(new URL('/login', request.url));
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
