"use client";

import { useEffect, useState } from "react";
import { Loader2, AlertCircle, CheckCircle2, XCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { getHealth, getReady, type ReadyResponse } from "@/lib/api/ops";

const POLL_INTERVAL_MS = 5_000;

export default function OpsStatusPage() {
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [ready, setReady] = useState<ReadyResponse | null>(null);
  const [readyError, setReadyError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = async () => {
    setIsLoading(true);
    try {
      const health = await getHealth();
      setHealthOk(health.status === "ok");
    } catch {
      setHealthOk(false);
    }

    try {
      const readyData = await getReady();
      setReady(readyData);
      setReadyError(null);
    } catch (err) {
      setReady(null);
      setReadyError(err instanceof Error ? err.message : "Readiness check failed");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[#1f2335]">System Status</h2>
        <p className="text-sm text-slate-500">
          Live platform health and readiness probes.
        </p>
      </div>

      {isLoading && healthOk === null ? (
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="size-4 animate-spin" />
          Checking status...
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">Liveness</span>
            <Badge variant={healthOk ? "default" : "destructive"}>
              {healthOk ? "Healthy" : "Unhealthy"}
            </Badge>
          </div>
          <div className="mt-4 flex items-center gap-2">
            {healthOk ? (
              <CheckCircle2 className="size-5 text-emerald-500" />
            ) : (
              <XCircle className="size-5 text-red-500" />
            )}
            <span className="font-medium text-slate-900">
              {healthOk ? "Service is up" : "Service is not responding"}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">Readiness</span>
            <Badge variant={ready ? "default" : "destructive"}>
              {ready ? "Ready" : "Not Ready"}
            </Badge>
          </div>
          <div className="mt-4 flex items-center gap-2">
            {ready ? (
              <CheckCircle2 className="size-5 text-emerald-500" />
            ) : (
              <AlertCircle className="size-5 text-red-500" />
            )}
            <span className="font-medium text-slate-900">
              {ready ? "All dependencies healthy" : "Dependency unavailable"}
            </span>
          </div>
        </div>
      </div>

      {readyError && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>{readyError}</AlertDescription>
        </Alert>
      )}

      {ready?.dependencies && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-500">
            Dependencies
          </h3>
          <div className="space-y-2">
            {Object.entries(ready.dependencies).map(([name, depStatus]) => (
              <div
                key={name}
                className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2"
              >
                <span className="text-sm font-medium text-slate-700 capitalize">
                  {name}
                </span>
                <Badge variant={depStatus === "ok" ? "default" : "destructive"}>
                  {depStatus}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
