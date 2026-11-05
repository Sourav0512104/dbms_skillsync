import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { Dashboard } from "@/components/dashboard";

export default async function DashboardPage() {
  const session = (await cookies()).get("skillsync_session");
  if (!session) redirect("/login");

  return <Dashboard />;
}
