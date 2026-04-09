import { redirect } from "next/navigation";

export default function Home() {
  // Root always redirects — dashboard requires token-validated cookie
  redirect("/dashboard");
}
