import { NextResponse } from "next/server";

import { newCsrfToken, setCsrfCookie } from "@/lib/server-auth";

export async function GET() {
  const token = newCsrfToken();
  const response = NextResponse.json({ csrf_token: token });
  setCsrfCookie(response, token);
  return response;
}
