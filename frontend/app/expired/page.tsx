export default function ExpiredPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
      <div className="text-center max-w-md px-6">
        <div className="text-5xl mb-4">⏰</div>
        <h1 className="text-xl font-bold text-slate-200 mb-2">Session Expired</h1>
        <p className="text-slate-400 text-sm mb-6">Your dashboard session has expired.</p>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-left text-sm text-slate-400">
          <p>Send <code className="text-cyan-400 font-mono">/web</code> to the Telegram bot to get a new access link.</p>
        </div>
      </div>
    </div>
  );
}
