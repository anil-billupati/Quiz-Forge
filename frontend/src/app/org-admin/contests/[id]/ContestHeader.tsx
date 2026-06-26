"use client";

import { useState } from "react";
import { Pencil, Trash2, Trophy, Calendar, LayoutList } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { ContestOut } from "@/lib/api/contests";
import { isDraft, lifecycleStatusLabel } from "@/lib/contest-status";
import ContestMetadataDialog from "./ContestMetadataDialog";
import ContestDeleteDialog from "./ContestDeleteDialog";

interface ContestHeaderProps {
  contest: ContestOut;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ContestHeader({ contest }: ContestHeaderProps) {
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  const editable = isDraft(contest.lifecycle_status);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">{contest.name}</h1>
            <Badge
              variant="secondary"
              className={cn(
                "border-0 font-medium capitalize",
                contest.lifecycle_status === "DRAFT" && "bg-slate-100 text-slate-600",
                contest.lifecycle_status === "PUBLISHED" && "bg-[#f05a22]/10 text-[#d94d1a]",
                contest.lifecycle_status === "REGISTRATION_OPEN" && "bg-blue-50 text-blue-600",
                contest.lifecycle_status === "REGISTRATION_CLOSED" && "bg-amber-50 text-amber-600",
                contest.lifecycle_status === "SCHEDULED" && "bg-purple-50 text-purple-600",
                contest.lifecycle_status === "LIVE" && "bg-red-50 text-red-600",
                (contest.lifecycle_status === "COMPLETED" || contest.lifecycle_status === "ARCHIVED") &&
                  "bg-emerald-50 text-emerald-600"
              )}
            >
              {lifecycleStatusLabel(contest.lifecycle_status)}
            </Badge>
            <Badge
              variant="outline"
              className="border-slate-200 font-medium capitalize text-slate-600"
            >
              {contest.structure.toLowerCase()}
            </Badge>
          </div>

          {contest.description ? (
            <p className="max-w-2xl text-sm text-slate-600">{contest.description}</p>
          ) : (
            <p className="text-sm italic text-slate-400">No description provided.</p>
          )}

          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-500">
            <span className="flex items-center gap-1.5">
              <Calendar className="size-4" />
              {contest.scheduled_start_at
                ? formatDateTime(contest.scheduled_start_at)
                : "Not scheduled"}
            </span>
            <span className="flex items-center gap-1.5">
              <Trophy className="size-4" />
              {contest.group_score_rollup
                ? contest.group_score_rollup.replace(/_/g, " ")
                : "No rollup"}
            </span>
            <span className="flex items-center gap-1.5">
              <LayoutList className="size-4" />
              Created {formatDate(contest.created_at)}
            </span>
          </div>
        </div>

        <TooltipProvider>
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    disabled={!editable}
                    onClick={() => setIsEditOpen(true)}
                  >
                    <Pencil className="size-4" />
                    Edit
                  </Button>
                </span>
              </TooltipTrigger>
              {!editable && (
                <TooltipContent>
                  <p>Editing is only available while the contest is in Draft.</p>
                </TooltipContent>
              )}
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-red-600 hover:text-red-700 hover:bg-red-50"
                    disabled={!editable}
                    onClick={() => setIsDeleteOpen(true)}
                  >
                    <Trash2 className="size-4" />
                    Delete
                  </Button>
                </span>
              </TooltipTrigger>
              {!editable && (
                <TooltipContent>
                  <p>Deletion is only available while the contest is in Draft.</p>
                </TooltipContent>
              )}
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>

      <ContestMetadataDialog
        contest={contest}
        open={isEditOpen}
        onOpenChange={setIsEditOpen}
      />
      <ContestDeleteDialog
        contest={contest}
        open={isDeleteOpen}
        onOpenChange={setIsDeleteOpen}
      />
    </div>
  );
}
