import { Loader2 } from "lucide-react";

export default function UsersLoading() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="size-6 animate-spin text-slate-400" />
    </div>
  );
}
