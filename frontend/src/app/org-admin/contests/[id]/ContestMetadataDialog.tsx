"use client";

import { useState, useTransition } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { ContestOut } from "@/lib/api/contests";
import { updateContestMetadata } from "./actions";

interface ContestMetadataDialogProps {
  contest: ContestOut;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function ContestMetadataDialog({
  contest,
  open,
  onOpenChange,
}: ContestMetadataDialogProps) {
  const [name, setName] = useState(contest.name);
  const [description, setDescription] = useState(contest.description ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const validate = (): boolean => {
    const nextErrors: Record<string, string> = {};
    if (!name.trim()) nextErrors.name = "Contest name is required";
    if (name.trim().length > 255) nextErrors.name = "Name must be 255 characters or less";
    if (description.trim().length > 2000) nextErrors.description = "Description must be 2000 characters or less";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = () => {
    setApiError(null);
    if (!validate()) return;

    startTransition(async () => {
      try {
        await updateContestMetadata(contest.id, {
          name: name.trim(),
          description: description.trim() || undefined,
        });
        onOpenChange(false);
      } catch (err) {
        setApiError(err instanceof Error ? err.message : "Failed to update contest.");
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Contest</DialogTitle>
          <DialogDescription>Update the contest name and description.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {apiError && (
            <Alert variant="destructive">
              <AlertDescription>{apiError}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Contest Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter contest name"
              disabled={isPending}
            />
            {errors.name && <p className="text-sm text-red-600">{errors.name}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter contest description"
              rows={4}
              disabled={isPending}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description}</p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isPending}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
