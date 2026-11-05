import { NextRequest } from "next/server";

import { authenticate } from "@/lib/auth-route";

export async function POST(request: NextRequest) {
  return authenticate(request, "register");
}
