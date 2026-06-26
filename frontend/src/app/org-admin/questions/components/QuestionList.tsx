"use client";

import { Pencil, Trash2, HelpCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { QuestionResponse } from "@/lib/api/questions";
import type { GroupOut } from "@/lib/api/groups";
import QuestionListSkeleton from "./QuestionListSkeleton";

interface QuestionListProps {
  questions: QuestionResponse[];
  groups: GroupOut[];
  editable?: boolean;
  isLoading?: boolean;
  onEdit: (question: QuestionResponse) => void;
  onDelete: (question: QuestionResponse) => void;
}

export default function QuestionList({
  questions,
  groups,
  editable = false,
  isLoading = false,
  onEdit,
  onDelete,
}: QuestionListProps) {
  const groupName = (groupId: string | null) =>
    groups.find((g) => g.id === groupId)?.name ?? "—";

  if (isLoading) {
    return <QuestionListSkeleton />;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-100 bg-slate-50 hover:bg-slate-50">
            <TableHead className="w-20 text-sm font-medium text-slate-500">#</TableHead>
            <TableHead className="text-sm font-medium text-slate-500">Question</TableHead>
            <TableHead className="w-36 text-sm font-medium text-slate-500">Group</TableHead>
            <TableHead className="w-28 text-sm font-medium text-slate-500">Options</TableHead>
            <TableHead className="w-40 text-sm font-medium text-slate-500">Correct</TableHead>
            {editable && <TableHead className="w-24 text-right text-sm font-medium text-slate-500">Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {questions.map((question) => {
            const correctOption = question.options.find((o) => o.is_correct);
            return (
              <TableRow
                key={question.id}
                className="border-slate-50 hover:bg-slate-50/50"
              >
                <TableCell className="py-4 text-sm font-medium text-slate-500">
                  {question.sequence}
                </TableCell>
                <TableCell className="py-4">
                  <div className="font-medium text-slate-900">{question.text}</div>
                  {question.explanation && (
                    <div className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                      <HelpCircle className="size-3" />
                      {question.explanation}
                    </div>
                  )}
                </TableCell>
                <TableCell className="py-4 text-sm text-slate-600">
                  {groupName(question.group_id)}
                </TableCell>
                <TableCell className="py-4 text-sm text-slate-600">
                  <Badge variant="outline" className="border-slate-200 text-slate-600">
                    {question.options.length}
                  </Badge>
                </TableCell>
                <TableCell className="py-4">
                  {correctOption ? (
                    <div className="flex items-center gap-1.5 text-sm text-emerald-700">
                      <CheckCircle2 className="size-4" />
                      <span className="truncate max-w-32">{correctOption.text}</span>
                    </div>
                  ) : (
                    <span className="text-sm text-red-600">No correct option</span>
                  )}
                </TableCell>
                {editable && (
                  <TableCell className="py-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onEdit(question)}
                        className="text-slate-500 hover:text-[#d94d1a]"
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onDelete(question)}
                        className="text-slate-500 hover:text-red-600"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </TableCell>
                )}
              </TableRow>
            );
          })}

          {questions.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={editable ? 6 : 5}
                className="h-40 text-center text-slate-400"
              >
                <div className="flex flex-col items-center gap-2">
                  <HelpCircle className="size-8 text-slate-300" />
                  <p>No questions found for this contest.</p>
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
