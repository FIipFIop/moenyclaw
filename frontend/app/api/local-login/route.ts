import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

// Use the internal backend URL — this runs server-side in Node.js
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    // 1. Get a local token from backend
    const tokenRes = await fetch(`${BACKEND}/api/tokens/local`, {
      cache: "no-store",
    });

    if (!tokenRes.ok) {
      const body = await tokenRes.text();
      return new NextResponse(
        `<p>Backend refused: ${tokenRes.status} ${body}</p>`,
        { status: 403, headers: { "Content-Type": "text/html" } }
      );
    }

    const { token } = await tokenRes.json();

    // 2. Validate it (marks it used + proves it works)
    const validateRes = await fetch(`${BACKEND}/api/tokens/${token}/validate`, {
      cache: "no-store",
    });

    if (!validateRes.ok) {
      return new NextResponse(`<p>Token validation failed</p>`, {
        status: 500,
        headers: { "Content-Type": "text/html" },
      });
    }

    // 3. Set session cookie and redirect to dashboard
    cookies().set("mc_session", token, {
      httpOnly: true,
      sameSite: "lax",
      maxAge: 3600,
      path: "/",
    });

    return NextResponse.redirect(new URL("/dashboard", req.url));
  } catch (err: any) {
    return new NextResponse(
      `<html><body style="font-family:sans-serif;background:#0a0e1a;color:#e2e8f0;padding:2rem">
        <h2>⚠️ Backend unreachable</h2>
        <p>Could not connect to <code>${BACKEND}</code></p>
        <p style="color:#64748b;font-size:0.85rem">${err?.message || err}</p>
        <p style="margin-top:1rem;color:#64748b">Make sure the backend is running:<br>
        <code style="color:#22d3ee">cd backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000</code></p>
      </body></html>`,
      { status: 503, headers: { "Content-Type": "text/html" } }
    );
  }
}
