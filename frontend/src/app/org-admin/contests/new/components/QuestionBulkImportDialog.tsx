"use client";

import { useState } from "react";
import { Upload, Loader2, AlertCircle, FileCheck, Download } from "lucide-react";
import { bulkImportQuestions, type QuestionResponse } from "@/lib/api/questions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";

const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2 MB

interface QuestionBulkImportDialogProps {
  contestId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (imported: QuestionResponse[]) => void;
}

export default function QuestionBulkImportDialog({
  contestId,
  open,
  onOpenChange,
  onSuccess,
}: QuestionBulkImportDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [importedCount, setImportedCount] = useState<number | null>(null);

  const validate = (selected: File): string | null => {
    if (selected.type !== "text/csv" && !selected.name.endsWith(".csv")) {
      return "Please upload a CSV file.";
    }
    if (selected.size > MAX_FILE_SIZE) {
      return "File size must be less than 2 MB.";
    }
    return null;
  };

  const handleFile = (selected: File | null) => {
    setApiError(null);
    setImportedCount(null);
    if (!selected) {
      setFile(null);
      return;
    }
    const error = validate(selected);
    if (error) {
      setApiError(error);
      setFile(null);
      return;
    }
    setFile(selected);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!file || !contestId) return;
    setApiError(null);
    setIsLoading(true);
    try {
      const imported = await bulkImportQuestions(contestId, file);
      setImportedCount(imported.length);
      onSuccess?.(imported);
    } catch (err) {
      setImportedCount(null);
      setApiError(err instanceof Error ? err.message : "Failed to import questions.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (isLoading) return;
    setFile(null);
    setApiError(null);
    setImportedCount(null);
    onOpenChange(false);
  };

  const downloadSampleCsv = () => {
    const rows = [
      "sequence,text,explanation,group_id,option_1,option_2,option_3,correct_option",
      '1,"What is 2 + 2?","Basic arithmetic",,3,4,5,2',
      '2,"Which data structure is LIFO?",,,Stack,Queue,Heap,1',
    ];
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "question-import-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Bulk Import Questions</DialogTitle>
          <DialogDescription>
            Upload a CSV with columns: <code>sequence</code>, <code>text</code>,{" "}
            <code>correct_option</code>, and <code>option_1</code> ...{" "}
            <code>option_10</code>. Optional: <code>explanation</code>,{" "}
            <code>group_id</code>.
          </DialogDescription>
        </DialogHeader>

        {apiError && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertDescription>{apiError}</AlertDescription>
          </Alert>
        )}

        {importedCount !== null && (
          <Alert>
            <FileCheck className="size-4" />
            <AlertDescription>
              Successfully imported {importedCount} question
              {importedCount === 1 ? "" : "s"}.
            </AlertDescription>
          </Alert>
        )}

        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${
            dragActive
              ? "border-[#f05a22] bg-[#f05a22]/5"
              : "border-slate-300 bg-slate-50"
          }`}
        >
          {file ? (
            <>
              <FileCheck className="size-8 text-emerald-500" />
              <p className="mt-3 font-medium text-slate-900">{file.name}</p>
              <p className="text-sm text-slate-500">
                {(file.size / 1024).toFixed(1)} KB
              </p>
              <Button
                type="button"
                variant="link"
                onClick={() => handleFile(null)}
                className="mt-2 text-[#d94d1a]"
              >
                Choose a different file
              </Button>
            </>
          ) : (
            <>
              <Upload className="size-8 text-slate-400" />
              <p className="mt-3 text-center text-sm font-medium text-slate-900">
                Drag and drop a CSV file, or{" "}
                <label className="cursor-pointer text-[#d94d1a] hover:text-[#b83f15]">
                  browse
                  <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                  />
                </label>
              </p>
            </>
          )}
        </div>

        <DialogFooter className="flex-col gap-3 sm:flex-row sm:justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={downloadSampleCsv}
            className="gap-1.5"
          >
            <Download className="size-4" />
            Download Template
          </Button>
          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
            >
              {importedCount !== null ? "Done" : "Cancel"}
            </Button>
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={!file || !contestId || isLoading}
              className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
            >
              {isLoading && <Loader2 className="size-4 animate-spin" />}
              Import Questions
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
