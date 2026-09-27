export function LoadingState({ label = 'Loading ...' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
      <div className="mr-3 h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
      {label}
    </div>
  );
}
