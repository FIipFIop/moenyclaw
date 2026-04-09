import { redirect } from "next/navigation";

export default function LocalPage() {
  // Delegate to the API route which runs reliably in Node.js context
  redirect("/api/local-login");
}
