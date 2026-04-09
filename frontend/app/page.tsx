import { redirect } from "next/navigation";
import { cookies } from "next/headers";

export default function Home() {
  // If already has a session, go straight to dashboard
  const session = cookies().get("mc_session");
  if (session?.value) {
    redirect("/dashboard");
  }
  // Otherwise auto-login via local token (works on localhost)
  redirect("/local");
}
