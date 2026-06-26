"use client";

import { useState } from "react";
import { Loader2, Pencil, Trash2, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { GroupOut } from "@/lib/api/groups";

interface GroupRowProps {
  group: GroupOut;
  editable: boolean;
  onUpdate: (groupId: string, input: { name?: string; sequence?: number; weight?: number | null }) => void;
  onDelete: (groupId: string) => void;
}

export default function GroupRow({ group, editable, onUpdate, onDelete }: GroupRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(group.name);
  const [sequence, setSequence] = useState(String(group.sequence));
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSave = async () => {
    await onUpdate(group.id, {
      name: name.trim(),
      sequence: parseInt(sequence, 10),
    });
    setIsEditing(false);
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    await onDelete(group.id);
    setIsDeleting(false);
  };

  if (isEditing) {
    return (
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-end">
        <div className="flex-1 space-y-2">
          <label className="text-xs font-medium text-slate-500">Name</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isDeleting}
          />
        </div>
        <div className="w-24 space-y-2">
          <label className="text-xs font-medium text-slate-500">Sequence</label>
          <Input
            type="number"
            min={1}
            value={sequence}
            onChange={(e) => setSequence(e.target.value)}
            disabled={isDeleting}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={handleSave} disabled={!name.trim() || isDeleting}>
            <Check className="size-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setIsEditing(false);
              setName(group.name);
              setSequence(String(group.sequence));
            }}
            disabled={isDeleting}
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-slate-900">{group.name}</p>
        <p className="text-sm text-slate-500">Sequence {group.sequence}</p>
      </div>

      {editable ? (
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => setIsEditing(true)}>
            <Pencil className="size-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-red-600 hover:bg-red-50 hover:text-red-700"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Trash2 className="size-4" />
            )}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
