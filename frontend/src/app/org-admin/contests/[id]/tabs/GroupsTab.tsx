"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { ContestOut } from "@/lib/api/contests";
import { listGroups, createGroup, updateGroup, deleteGroup, type GroupOut } from "@/lib/api/groups";
import { isDraft } from "@/lib/contest-status";
import GroupRow from "../components/GroupRow";

interface GroupsTabProps {
  contest: ContestOut;
}

type LoadState = "loading" | "error" | "ready";

export default function GroupsTab({ contest }: GroupsTabProps) {
  const editable = isDraft(contest.lifecycle_status);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [apiError, setApiError] = useState<string | null>(null);
  const [groups, setGroups] = useState<GroupOut[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function loadGroups() {
      setLoadState("loading");
      setApiError(null);
      try {
        const data = await listGroups(contest.id);
        setGroups(data);
        setLoadState("ready");
      } catch (err) {
        setApiError(err instanceof Error ? err.message : "Failed to load groups.");
        setLoadState("error");
      }
    }

    loadGroups();
  }, [contest.id]);

  const handleAdd = async () => {
    if (!newName.trim()) return;
    setIsSubmitting(true);
    setApiError(null);
    try {
      const created = await createGroup(contest.id, {
        name: newName.trim(),
        sequence: groups.length + 1,
        weight: null,
      });
      setGroups([...groups, created]);
      setNewName("");
      setIsAdding(false);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to create group.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async (groupId: string, input: { name?: string; sequence?: number; weight?: number | null }) => {
    setApiError(null);
    try {
      const updated = await updateGroup(contest.id, groupId, input);
      setGroups((prev) =>
        prev.map((g) => (g.id === groupId ? updated : g)).sort((a, b) => a.sequence - b.sequence)
      );
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to update group.");
    }
  };

  const handleDelete = async (groupId: string) => {
    setApiError(null);
    try {
      await deleteGroup(contest.id, groupId);
      setGroups((prev) => prev.filter((g) => g.id !== groupId));
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to delete group.");
    }
  };

  if (loadState === "loading") {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white">
        <Loader2 className="size-6 animate-spin text-slate-400" />
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>{apiError ?? "Could not load groups."}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Groups</h3>
          <p className="text-sm text-slate-500">
            {editable
              ? "Manage groups for this contest."
              : "Groups are locked after the contest leaves Draft."}
          </p>
        </div>
        {editable && (
          <Button
            onClick={() => setIsAdding(true)}
            disabled={isAdding}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            <Plus className="size-4" />
            Add Group
          </Button>
        )}
      </div>

      {apiError && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      {isAdding && (
        <div className="mb-6 flex items-end gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex-1 space-y-2">
            <Label htmlFor="newGroupName">Group Name</Label>
            <Input
              id="newGroupName"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Group C"
              disabled={isSubmitting}
            />
          </div>
          <Button onClick={handleAdd} disabled={isSubmitting || !newName.trim()}>
            {isSubmitting && <Loader2 className="mr-2 size-4 animate-spin" />}
            Add
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setIsAdding(false);
              setNewName("");
            }}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        </div>
      )}

      <div className="space-y-3">
        {groups.map((group) => (
          <GroupRow
            key={group.id}
            group={group}
            editable={editable}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
        ))}

        {groups.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f05a22]/10">
              <Plus className="size-8 text-[#f05a22]" />
            </div>
            <h3 className="mt-6 text-lg font-semibold text-slate-900">No groups yet</h3>
            <p className="mt-2 max-w-sm text-sm text-slate-500">
              Add groups to organize participants for this contest.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
