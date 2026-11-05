import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ status: "signed_out" });
  response.cookies.set("skillsync_session", "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}
