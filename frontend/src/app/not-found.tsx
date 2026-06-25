import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center">
      <div className="max-w-md space-y-4">
        <h1 className="text-6xl font-bold text-[#f05a22]">404</h1>
        <h2 className="text-2xl font-bold text-slate-900">Page not found</h2>
        <p className="text-slate-600">
          The page you are looking for does not exist or has been moved.
        </p>
        <Button asChild className="bg-[#f05a22] text-white hover:bg-[#d94d1a]">
          <Link href="/login">Go to sign in</Link>
        </Button>
      </div>
    </div>
  );
}
