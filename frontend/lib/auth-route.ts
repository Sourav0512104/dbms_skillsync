import { NextRequest, NextResponse } from "next/server";

const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function authenticate(
  request: NextRequest,
  endpoint: "login" | "register",
) {
  let upstream: Response;
  try {
    upstream = await fetch(`${apiUrl}/auth/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    return NextResponse.json(
      { detail: "The SkillSync API is unavailable. Please try again shortly." },
      { status: 502 },
    );
  }

  const result = await upstream.json();
  if (!upstream.ok) {
    return NextResponse.json(result, { status: upstream.status });
  }

  const response = NextResponse.json({ user: result.user });
  response.cookies.set("skillsync_session", result.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60,
  });
  return response;
}
