"use client";

import { useState, useTransition } from "react";
import { Loader2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { ContestOut } from "@/lib/api/contests";
import { deleteContest } from "./actions";

interface ContestDeleteDialogProps {
  contest: ContestOut;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function ContestDeleteDialog({
  contest,
  open,
  onOpenChange,
}: ContestDeleteDialogProps) {
  const [apiError, setApiError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleDelete = () => {
    setApiError(null);
    startTransition(async () => {
      try {
        await deleteContest(contest.id);
        onOpenChange(false);
      } catch (err) {
        setApiError(err instanceof Error ? err.message : "Failed to delete contest.");
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-red-500" />
            Delete Contest
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete{" "}
            <span className="font-medium text-slate-900">{contest.name}</span>.
          </DialogDescription>
        </DialogHeader>

        {apiError && (
          <Alert variant="destructive">
            <AlertDescription>{apiError}</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleDelete}
            disabled={isPending}
            className="gap-1.5 bg-red-500 hover:bg-red-600"
          >
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Delete Contest
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
