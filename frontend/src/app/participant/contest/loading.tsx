export default function Loading() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-900 text-white">
      <div className="h-16 w-16 animate-spin rounded-full border-4 border-[#f05a22] border-t-transparent" />
      <p className="mt-4 text-sm text-slate-400">Loading contest...</p>
    </div>
  );
}
