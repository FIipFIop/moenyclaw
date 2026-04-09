import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { WebSocketProvider } from "@/components/providers/WebSocketProvider";
import { StatusBar } from "@/components/dashboard/StatusBar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = cookies().get("mc_session");
  if (!session?.value) {
    redirect("/expired");
  }

  return (
    <WebSocketProvider>
      <div className="min-h-screen flex flex-col">
        <StatusBar />
        <main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">
          {children}
        </main>
      </div>
    </WebSocketProvider>
  );
}
