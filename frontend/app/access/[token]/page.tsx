import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const API = process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";

interface Props {
  params: { token: string };
}

export default async function AccessPage({ params }: Props) {
  const { token } = params;

  let valid = false;
  let errorMsg = "Invalid or expired link.";

  try {
    const res = await fetch(`${API}/api/tokens/${token}/validate`, {
      method: "GET",
      cache: "no-store",
    });

    if (res.ok) {
      const data = await res.json();
      if (data.valid) {
        // Set session cookie (1 hour)
        cookies().set("mc_session", token, {
          httpOnly: true,
          sameSite: "lax",
          maxAge: 3600,
          path: "/",
        });
        valid = true;
      }
    } else if (res.status === 401) {
      const data = await res.json();
      errorMsg = data.detail || errorMsg;
    }
  } catch {
    errorMsg = "Could not reach the MoneyClaw backend.";
  }

  if (valid) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
      <div className="text-center max-w-md px-6">
        <div className="text-5xl mb-4">🔒</div>
        <h1 className="text-xl font-bold text-slate-200 mb-2">Link Expired</h1>
        <p className="text-slate-400 text-sm mb-6">{errorMsg}</p>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-left text-sm text-slate-400">
          <p>To get a new link, send <code className="text-cyan-400 font-mono">/web</code> to the Telegram bot.</p>
        </div>
      </div>
    </div>
  );
}
