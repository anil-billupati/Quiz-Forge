"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Upload, FileCheck, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { bulkImportParticipants } from "@/lib/api/users";
import ImportResultsTable from "./ImportResultsTable";

const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2 MB

export default function BulkImportForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof bulkImportParticipants>> | null>(
    null
  );

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
    setResult(null);
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
    if (!file) return;
    setApiError(null);
    setIsLoading(true);
    try {
      const data = await bulkImportParticipants(file);
      setResult(data);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to import participants.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">Upload CSV</h3>
        <p className="mt-1 text-sm text-slate-500">
          CSV must contain headers: <code className="text-[#d94d1a]">email</code>,{" "}
          <code className="text-[#d94d1a]">first_name</code>,{" "}
          <code className="text-[#d94d1a]">last_name</code>.
        </p>

        {apiError && (
          <Alert variant="destructive" className="mt-4">
            <AlertCircle className="size-4" />
            <AlertDescription>{apiError}</AlertDescription>
          </Alert>
        )}

        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`mt-4 flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${
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
              <p className="mt-3 text-sm font-medium text-slate-900">
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

        <div className="mt-6 flex items-center justify-end gap-3">
          <Button variant="outline" onClick={() => router.back()} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!file || isLoading}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            {isLoading && <Loader2 className="size-4 animate-spin" />}
            Import Participants
          </Button>
        </div>
      </div>

      {result && <ImportResultsTable result={result} />}
    </div>
  );
}
