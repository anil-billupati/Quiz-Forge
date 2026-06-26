"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Play,
  Trophy,
  Loader2,
  AlertCircle,
  LogOut,
  LogIn,
  LayoutGrid,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { getContests, type ContestOut } from "@/lib/api/contests";
import {
  getMyRegistration,
  registerForContest,
  withdrawRegistration,
  type RegistrationResponse,
} from "@/lib/api/registrations";

interface ContestWithRegistration {
  contest: ContestOut;
  registration: RegistrationResponse | null;
}

export default function ParticipantDashboardPage() {
  const router = useRouter();
  const [items, setItems] = useState<ContestWithRegistration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);

  const load = async () => {
    setIsLoading(true);
    setApiError(null);
    try {
      const contests = await getContests(undefined, 100);
      const relevant = contests.filter(
        (c) =>
          c.lifecycle_status === "REGISTRATION_OPEN" ||
          c.lifecycle_status === "LIVE"
      );

      const withRegistrations = await Promise.all(
        relevant.map(async (contest) => {
          try {
            const registration = await getMyRegistration(contest.id);
            return { contest, registration };
          } catch {
            return { contest, registration: null };
          }
        })
      );

      setItems(withRegistrations);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to load contests.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRegister = async (contestId: string) => {
    setActionId(contestId);
    setApiError(null);
    try {
      await registerForContest(contestId);
      await load();
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to register.");
    } finally {
      setActionId(null);
    }
  };

  const handleWithdraw = async (contestId: string, registrationId: string) => {
    setActionId(contestId);
    setApiError(null);
    try {
      await withdrawRegistration(contestId, registrationId);
      await load();
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to withdraw.");
    } finally {
      setActionId(null);
    }
  };

  const canJoinLive = (
    registration: RegistrationResponse | null,
    status: string
  ) => {
    return (
      status === "LIVE" &&
      (registration?.status === "REGISTERED" || registration?.status === "ACTIVE")
    );
  };

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-[#1f2335]">My Dashboard</h2>
        <p className="text-sm text-slate-500">
          Active contests you can register for or join live.
        </p>
      </div>

      {apiError && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="size-4" />
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-16 text-center">
          <Loader2 className="size-8 animate-spin text-[#f05a22]" />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
            <LayoutGrid className="size-8 text-[#f05a22]" />
          </div>
          <h3 className="mt-6 text-lg font-semibold text-[#1f2335]">
            No contests right now
          </h3>
          <p className="mt-2 max-w-sm text-sm text-slate-500">
            Check back later for contests that are open for registration or live.
          </p>
          <Button
            asChild
            className="mt-6 gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            <a href="/participant/profile">
              <Trophy className="size-4" />
              Go to Profile
            </a>
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map(({ contest, registration }) => (
            <div
              key={contest.id}
              className="rounded-xl border border-slate-200 bg-white p-5"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-slate-900">{contest.name}</h3>
                    <Badge
                      variant={
                        contest.lifecycle_status === "LIVE" ? "default" : "secondary"
                      }
                    >
                      {contest.lifecycle_status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    {contest.description || "No description"}
                  </p>
                  {registration && (
                    <p className="mt-2 text-sm">
                      Your registration:{" "}
                      <span className="font-medium text-slate-900">
                        {registration.status}
                      </span>
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {canJoinLive(registration, contest.lifecycle_status) ? (
                    <Button
                      onClick={() =>
                        router.push(`/participant/contest/live?contestId=${contest.id}`)
                      }
                      className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
                    >
                      <Play className="size-4" />
                      Join Live
                    </Button>
                  ) : null}

                  {!registration && contest.lifecycle_status === "REGISTRATION_OPEN" && (
                    <Button
                      onClick={() => handleRegister(contest.id)}
                      disabled={actionId === contest.id}
                      className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
                    >
                      {actionId === contest.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <LogIn className="size-4" />
                      )}
                      Register
                    </Button>
                  )}

                  {registration &&
                    contest.lifecycle_status === "REGISTRATION_OPEN" && (
                      <Button
                        variant="outline"
                        onClick={() => handleWithdraw(contest.id, registration.id)}
                        disabled={actionId === contest.id}
                        className="gap-1.5"
                      >
                        {actionId === contest.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <LogOut className="size-4" />
                        )}
                        Withdraw
                      </Button>
                    )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
