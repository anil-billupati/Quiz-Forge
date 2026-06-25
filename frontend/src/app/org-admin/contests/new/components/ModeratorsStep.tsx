"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Search, X, Check, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  listModerators,
  createModerator,
  type ModeratorOut,
} from "@/lib/api/moderators";
import type { ContestModerator, RevealMode } from "../types";

interface ModeratorsStepProps {
  revealMode: RevealMode;
  selected: ContestModerator[];
  newModeratorIds: string[];
  errors: Record<string, string>;
  onChange: (selected: ContestModerator[], newModeratorIds: string[]) => void;
}

type LoadState = "loading" | "error" | "ready";

function toContestModerator(user: ModeratorOut, isNew = false): ContestModerator {
  return {
    id: user.id,
    email: user.email,
    first_name: user.first_name,
    last_name: user.last_name,
    status: user.status,
    isNewlyCreated: isNew,
  };
}

export default function ModeratorsStep({
  revealMode,
  selected,
  newModeratorIds,
  errors,
  onChange,
}: ModeratorsStepProps) {
  const isRequired = revealMode === "MODERATOR_CONTROLLED";

  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [apiError, setApiError] = useState<string | null>(null);
  const [available, setAvailable] = useState<ContestModerator[]>([]);
  const [search, setSearch] = useState("");

  const [isCreating, setIsCreating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createForm, setCreateForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
  });
  const [createErrors, setCreateErrors] = useState<Record<string, string>>({});

  const selectedIds = useMemo(
    () => new Set(selected.map((m) => m.id)),
    [selected]
  );

  const load = async () => {
    setLoadState("loading");
    setApiError(null);
    try {
      const users = await listModerators();
      const mapped = users.map((u) => toContestModerator(u, newModeratorIds.includes(u.id)));
      // Preserve any newly created moderators that may not yet appear in the list.
      const existingIds = new Set(mapped.map((m) => m.id));
      const extra = selected.filter((s) => !existingIds.has(s.id));
      setAvailable([...mapped, ...extra]);
      setLoadState("ready");
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to load moderators.");
      setLoadState("error");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return available;
    return available.filter(
      (m) =>
        m.email.toLowerCase().includes(q) ||
        `${m.first_name} ${m.last_name}`.toLowerCase().includes(q)
    );
  }, [available, search]);

  const toggleModerator = (moderator: ContestModerator) => {
    if (selectedIds.has(moderator.id)) {
      onChange(
        selected.filter((m) => m.id !== moderator.id),
        newModeratorIds
      );
    } else {
      onChange([...selected, moderator], newModeratorIds);
    }
  };

  const removeSelected = (id: string) => {
    onChange(
      selected.filter((m) => m.id !== id),
      newModeratorIds
    );
  };

  const validateCreateForm = (): boolean => {
    const errs: Record<string, string> = {};
    if (!createForm.first_name.trim()) errs.first_name = "First name is required.";
    if (!createForm.last_name.trim()) errs.last_name = "Last name is required.";
    if (!createForm.email.trim()) errs.email = "Email is required.";
    if (!createForm.password.trim()) errs.password = "Password is required.";
    if (createForm.password.trim().length < 8) errs.password = "Password must be at least 8 characters.";
    setCreateErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleCreate = async () => {
    if (!validateCreateForm()) return;
    setIsSubmitting(true);
    setApiError(null);
    try {
      const created = await createModerator(createForm);
      const moderator = toContestModerator(created, true);
      setAvailable((prev) => [moderator, ...prev.filter((m) => m.id !== moderator.id)]);
      onChange([...selected, moderator], [...newModeratorIds, moderator.id]);
      setCreateForm({ first_name: "", last_name: "", email: "", password: "" });
      setIsCreating(false);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to create moderator.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">
              Moderator Assignment
            </h3>
            <p className="text-sm text-slate-500">
              Choose who will manage this contest.
            </p>
          </div>
          {isRequired && (
            <Badge className="w-fit bg-red-50 text-red-600 hover:bg-red-50">
              Required
            </Badge>
          )}
        </div>

        {isRequired && (
          <Alert className="mb-4 border-blue-200 bg-blue-50 text-blue-900">
            <AlertDescription className="text-blue-800">
              This contest uses <strong>Moderator Controlled</strong> reveal mode,
              so at least one moderator must be assigned before publishing.
            </AlertDescription>
          </Alert>
        )}

        {apiError && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="size-4" />
            <AlertDescription>{apiError}</AlertDescription>
          </Alert>
        )}

        {errors.moderators && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{errors.moderators}</AlertDescription>
          </Alert>
        )}

        {selected.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {selected.map((moderator) => (
              <div
                key={moderator.id}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm",
                  moderator.isNewlyCreated
                    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "border-slate-200 bg-slate-50 text-slate-700"
                )}
              >
                <span className="font-medium">
                  {moderator.first_name} {moderator.last_name}
                </span>
                {moderator.isNewlyCreated && (
                  <Badge
                    variant="outline"
                    className="border-emerald-200 text-emerald-700"
                  >
                    Invite sent
                  </Badge>
                )}
                <button
                  type="button"
                  onClick={() => removeSelected(moderator.id)}
                  className="text-slate-400 hover:text-red-600"
                  aria-label={`Remove ${moderator.first_name} ${moderator.last_name}`}
                >
                  <X className="size-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search moderators by name or email"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-xl border-slate-200 bg-white py-3 pl-10 text-sm"
          />
        </div>

        <div className="space-y-2">
          {loadState === "loading" && (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-16 w-full animate-pulse rounded-xl bg-slate-100" />
              ))}
            </div>
          )}

          {loadState === "error" && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
              Could not load moderators.
              <Button
                type="button"
                variant="link"
                onClick={load}
                className="ml-1 h-auto p-0 text-[#d94d1a]"
              >
                Retry
              </Button>
            </div>
          )}

          {loadState === "ready" &&
            filtered.map((moderator) => {
              const isSelected = selectedIds.has(moderator.id);
              return (
                <button
                  key={moderator.id}
                  type="button"
                  onClick={() => toggleModerator(moderator)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-xl border p-4 text-left transition-colors",
                    isSelected
                      ? "border-[#f05a22] bg-[#f05a22]/5"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  )}
                >
                  <div>
                    <p className="font-medium text-slate-900">
                      {moderator.first_name} {moderator.last_name}
                    </p>
                    <p className="text-sm text-slate-500">{moderator.email}</p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={cn(
                          "border-0 text-xs",
                          moderator.status === "ACTIVE"
                            ? "bg-emerald-50 text-emerald-600"
                            : "bg-slate-100 text-slate-600"
                        )}
                      >
                        {moderator.status.toLowerCase()}
                      </Badge>
                      {moderator.isNewlyCreated && (
                        <Badge
                          variant="outline"
                          className="border-emerald-200 bg-emerald-50 text-xs text-emerald-700"
                        >
                          Invite sent
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full",
                      isSelected
                        ? "bg-[#f05a22] text-white"
                        : "border border-slate-200 bg-white text-slate-400"
                    )}
                  >
                    {isSelected ? <Check className="size-4" /> : <Plus className="size-4" />}
                  </div>
                </button>
              );
            })}

          {loadState === "ready" && filtered.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
              {search.trim()
                ? "No moderators match your search."
                : "No moderators found. Create one below to get started."}
            </div>
          )}
        </div>

        <div className="mt-6 border-t border-slate-100 pt-6">
          {!isCreating ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCreating(true)}
              className="gap-1.5 border-dashed border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            >
              <Plus className="size-4" />
              Create and assign new moderator
            </Button>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5">
              <h4 className="mb-4 text-sm font-semibold text-slate-900">
                Create new moderator
              </h4>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="modFirstName">First Name</Label>
                  <Input
                    id="modFirstName"
                    value={createForm.first_name}
                    onChange={(e) =>
                      setCreateForm((prev) => ({ ...prev, first_name: e.target.value }))
                    }
                    placeholder="e.g. Jane"
                    className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm"
                  />
                  {createErrors.first_name && (
                    <p className="text-sm text-red-600">{createErrors.first_name}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="modLastName">Last Name</Label>
                  <Input
                    id="modLastName"
                    value={createForm.last_name}
                    onChange={(e) =>
                      setCreateForm((prev) => ({ ...prev, last_name: e.target.value }))
                    }
                    placeholder="e.g. Doe"
                    className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm"
                  />
                  {createErrors.last_name && (
                    <p className="text-sm text-red-600">{createErrors.last_name}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="modEmail">Email</Label>
                  <Input
                    id="modEmail"
                    type="email"
                    value={createForm.email}
                    onChange={(e) =>
                      setCreateForm((prev) => ({ ...prev, email: e.target.value }))
                    }
                    placeholder="jane@example.com"
                    className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm"
                  />
                  {createErrors.email && (
                    <p className="text-sm text-red-600">{createErrors.email}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="modPassword">Password</Label>
                  <Input
                    id="modPassword"
                    type="password"
                    value={createForm.password}
                    onChange={(e) =>
                      setCreateForm((prev) => ({ ...prev, password: e.target.value }))
                    }
                    placeholder="Set an initial password"
                    className="rounded-xl border-slate-200 bg-white px-4 py-3 text-sm"
                  />
                  {createErrors.password && (
                    <p className="text-sm text-red-600">{createErrors.password}</p>
                  )}
                </div>
              </div>
              <div className="mt-4 flex items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setIsCreating(false);
                    setCreateErrors({});
                  }}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleCreate}
                  disabled={isSubmitting}
                  className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
                >
                  {isSubmitting && <Loader2 className="size-4 animate-spin" />}
                  Create & Assign
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
