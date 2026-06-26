"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Upload, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ContestOut } from "@/lib/api/contests";
import type { GroupOut } from "@/lib/api/groups";
import {
  listQuestions,
  createQuestion,
  updateQuestion,
  replaceOptions,
  deleteQuestion,
  type QuestionResponse,
  type QuestionCreateRequest,
  type QuestionUpdateRequest,
} from "@/lib/api/questions";
import { listGroups } from "@/lib/api/groups";
import { isDraft } from "@/lib/contest-status";
import QuestionBulkImportDialog from "@/app/org-admin/contests/new/components/QuestionBulkImportDialog";
import QuestionForm, { type QuestionFormValues } from "./QuestionForm";
import QuestionList from "./QuestionList";

interface QuestionManagerProps {
  contest: ContestOut;
}

type LoadState = "loading" | "error" | "ready";
type DialogMode = "create" | "edit" | "delete" | null;

export default function QuestionManager({ contest }: QuestionManagerProps) {
  const editable = isDraft(contest.lifecycle_status);

  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [apiError, setApiError] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuestionResponse[]>([]);
  const [groups, setGroups] = useState<GroupOut[]>([]);

  const [dialogMode, setDialogMode] = useState<DialogMode>(null);
  const [activeQuestion, setActiveQuestion] = useState<QuestionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  const defaultSequence = useMemo(() => {
    if (questions.length === 0) return 1;
    return Math.max(...questions.map((q) => q.sequence)) + 1;
  }, [questions]);

  const load = async () => {
    setLoadState("loading");
    setApiError(null);
    try {
      const [questionData, groupData] = await Promise.all([
        listQuestions(contest.id),
        contest.structure === "GROUPED" ? listGroups(contest.id) : Promise.resolve([]),
      ]);
      setQuestions(questionData);
      setGroups(groupData);
      setLoadState("ready");
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to load questions.");
      setLoadState("error");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contest.id, contest.structure]);

  const handleCreate = () => {
    setActiveQuestion(null);
    setDialogMode("create");
    setApiError(null);
  };

  const handleEdit = (question: QuestionResponse) => {
    setActiveQuestion(question);
    setDialogMode("edit");
    setApiError(null);
  };

  const handleDeletePrompt = (question: QuestionResponse) => {
    setActiveQuestion(question);
    setDialogMode("delete");
    setApiError(null);
  };

  const handleSubmit = async (values: QuestionFormValues) => {
    setIsSubmitting(true);
    setApiError(null);
    try {
      const optionPayload = values.options.map(({ text, is_correct }) => ({
        text,
        is_correct,
      }));

      if (dialogMode === "create") {
        const body: QuestionCreateRequest = {
          group_id: contest.structure === "GROUPED" ? values.group_id : null,
          sequence: values.sequence,
          text: values.text,
          explanation: values.explanation,
          options: optionPayload,
        };
        await createQuestion(contest.id, body);
      } else if (dialogMode === "edit" && activeQuestion) {
        const body: QuestionUpdateRequest = {
          group_id: contest.structure === "GROUPED" ? values.group_id : null,
          sequence: values.sequence,
          text: values.text,
          explanation: values.explanation,
        };
        await updateQuestion(contest.id, activeQuestion.id, body);
        await replaceOptions(contest.id, activeQuestion.id, {
          options: optionPayload,
        });
      }

      setDialogMode(null);
      setActiveQuestion(null);
      await load();
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to save question.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!activeQuestion) return;
    setIsSubmitting(true);
    setApiError(null);
    try {
      await deleteQuestion(contest.id, activeQuestion.id);
      setDialogMode(null);
      setActiveQuestion(null);
      await load();
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to delete question.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const closeDialog = () => {
    if (isSubmitting) return;
    setDialogMode(null);
    setActiveQuestion(null);
    setApiError(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Questions</h3>
          <p className="text-sm text-slate-500">
            {editable
              ? "Manage questions and correct answers."
              : "Questions are locked after the contest leaves Draft."}
          </p>
        </div>
        {editable && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setImportDialogOpen(true)}
              className="gap-1.5"
            >
              <Upload className="size-4" />
              Bulk Import
            </Button>
            <Button
              onClick={handleCreate}
              className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
            >
              <Plus className="size-4" />
              Add Question
            </Button>
          </div>
        )}
      </div>

      {apiError && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      {loadState === "error" ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <Alert variant="destructive">
            <AlertDescription>
              {apiError ?? "Could not load questions."}
            </AlertDescription>
          </Alert>
        </div>
      ) : (
        <QuestionList
          questions={questions}
          groups={groups}
          editable={editable}
          isLoading={loadState === "loading"}
          onEdit={handleEdit}
          onDelete={handleDeletePrompt}
        />
      )}

      <Dialog open={dialogMode === "create" || dialogMode === "edit"} onOpenChange={closeDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {dialogMode === "create" ? "Add Question" : "Edit Question"}
            </DialogTitle>
          </DialogHeader>
          <QuestionForm
            contestStructure={contest.structure as "NORMAL" | "GROUPED"}
            groups={groups}
            question={activeQuestion ?? undefined}
            defaultSequence={defaultSequence}
            onSubmit={handleSubmit}
            onCancel={closeDialog}
            isSubmitting={isSubmitting}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={dialogMode === "delete"} onOpenChange={closeDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Question</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600">
            Are you sure you want to delete this question? This action cannot be
            undone.
          </p>
          {activeQuestion && (
            <p className="rounded-lg bg-slate-50 p-3 text-sm font-medium text-slate-900">
              {activeQuestion.text}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={closeDialog} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Deleting..." : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <QuestionBulkImportDialog
        contestId={contest.id}
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onSuccess={async () => {
          setImportDialogOpen(false);
          await load();
        }}
      />
    </div>
  );
}
