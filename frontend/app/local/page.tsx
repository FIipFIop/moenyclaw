/**
 * Local access page — auto-generates a token and redirects to dashboard.
 * Only works when the backend is on localhost (token endpoint refuses remote IPs).
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const API = process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";

export default async function LocalPage() {
  let errorMsg: string | null = null;

  try {
    const res = await fetch(`${API}/api/tokens/local`, { cache: "no-store" });
    if (res.ok) {
      const { token } = await res.json();
      // Immediately validate it so we get the session cookie
      const validateRes = await fetch(`${API}/api/tokens/${token}/validate`, { cache: "no-store" });
      if (validateRes.ok) {
        cookies().set("mc_session", token, {
          httpOnly: true,
          sameSite: "lax",
          maxAge: 3600,
          path: "/",
        });
        redirect("/dashboard");
      }
    } else {
      const data = await res.json().catch(() => ({}));
      errorMsg = data.detail || `Backend returned ${res.status}`;
    }
  } catch (e) {
    errorMsg = "Could not reach backend at " + API;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
      <div className="text-center max-w-md px-6">
        <div className="text-5xl mb-4">⚠️</div>
        <h1 className="text-xl font-bold text-slate-200 mb-2">Local Access Failed</h1>
        <p className="text-slate-400 text-sm mb-4">{errorMsg}</p>
        <p className="text-slate-600 text-xs">
          This page only works when both the backend and your browser are on the same machine (localhost).
        </p>
      </div>
    </div>
  );
}
