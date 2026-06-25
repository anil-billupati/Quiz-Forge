"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, CheckCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  createContest,
  setContestConfiguration,
  transitionLifecycle,
  enableWildcard,
  disableWildcard,
} from "@/lib/api/contests";
import { createGroup } from "@/lib/api/groups";
import { setGroupConfiguration } from "@/lib/api/configurations";
import { formConfigToBlockRequest } from "@/lib/contest-config";
import WizardStepper from "./components/WizardStepper";
import ContestInfoStep from "./components/ContestInfoStep";
import StructureStep from "./components/StructureStep";
import ConfigurationStep from "./components/ConfigurationStep";
import QuestionsStep from "./components/QuestionsStep";
import ReviewStep from "./components/ReviewStep";
import {
  type ContestFormState,
  type ContestStructure,
  type ContestConfiguration,
  defaultConfiguration,
} from "./types";

const steps = [
  "Contest Info",
  "Structure",
  "Configuration",
  "Questions",
  "Review & Publish",
];

function getInitialState(): ContestFormState {
  return {
    info: {
      name: "",
      description: "",
      startAt: "",
      endAt: "",
    },
    structure: "NORMAL",
    groups: ["Group A", "Group B"],
    config: {
      default: { ...defaultConfiguration },
      byGroup: {},
    },
    questions: [],
  };
}

const wildcardMap: Record<
  keyof ContestConfiguration["wildcards"],
  "FIFTY_FIFTY" | "SECOND_CHANCE" | "SKIP"
> = {
  fiftyFifty: "FIFTY_FIFTY",
  secondChance: "SECOND_CHANCE",
  skip: "SKIP",
};

async function syncWildcards(
  configBlockId: string,
  wildcards: ContestConfiguration["wildcards"]
): Promise<void> {
  const entries = Object.entries(wildcards) as [
    keyof ContestConfiguration["wildcards"],
    boolean
  ][];

  await Promise.all(
    entries.map(async ([key, enabled]) => {
      const type = wildcardMap[key];
      if (enabled) {
        try {
          await enableWildcard(configBlockId, { type, eligibility: "ALL" });
        } catch (err) {
          // Ignore conflict if wildcard already exists.
          if (err instanceof Error && err.message.includes("already exists")) {
            return;
          }
          throw err;
        }
      } else {
        try {
          await disableWildcard(configBlockId, type);
        } catch (err) {
          // Ignore not-found if wildcard was never enabled.
          if (err instanceof Error && err.message.includes("not found")) {
            return;
          }
          throw err;
        }
      }
    })
  );
}

export default function CreateContestPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<ContestFormState>(getInitialState);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [contestId, setContestId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const validateStep = (currentStep: number): boolean => {
    const nextErrors: Record<string, string> = {};

    if (currentStep === 1) {
      if (!form.info.name.trim()) {
        nextErrors.name = "Contest name is required";
      }
      if (!form.info.startAt) {
        nextErrors.startAt = "Start date & time is required";
      }
      if (!form.info.endAt) {
        nextErrors.endAt = "End date & time is required";
      }
      if (
        form.info.startAt &&
        form.info.endAt &&
        new Date(form.info.startAt) >= new Date(form.info.endAt)
      ) {
        nextErrors.endAt = "End time must be after start time";
      }
    }

    if (currentStep === 2) {
      if (form.structure === "GROUPED") {
        if (form.groups.length < 2) {
          nextErrors.groups = "At least two groups are required";
        }
        if (form.groups.some((g) => !g.trim())) {
          nextErrors.groups = "Group names cannot be empty";
        }
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleCreateContest = async (): Promise<boolean> => {
    if (!validateStep(step)) return false;
    setIsLoading(true);
    setApiError(null);

    try {
      const contest = await createContest({
        name: form.info.name,
        structure: form.structure,
        description: form.info.description,
        group_score_rollup:
          form.structure === "GROUPED" ? "SUM" : undefined,
      });
      setContestId(contest.id);
      return true;
    } catch (err) {
      setApiError(
        err instanceof Error ? err.message : "Failed to create contest."
      );
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveConfiguration = async (): Promise<boolean> => {
    if (!contestId) {
      setApiError("Contest has not been created yet.");
      return false;
    }

    setIsLoading(true);
    setApiError(null);

    try {
      if (form.structure === "NORMAL") {
        const block = await setContestConfiguration(
          contestId,
          formConfigToBlockRequest(form.config.default)
        );
        await syncWildcards(block.id, form.config.default.wildcards);
      } else {
        // For GROUPED contests, create each group and save its configuration at group scope.
        // Grouped contests do not have a contest-level configuration block.
        const createdGroups = await Promise.all(
          form.groups.map((name, index) =>
            createGroup(contestId, {
              name,
              sequence: index + 1,
              weight: null,
            })
          )
        );

        await Promise.all(
          createdGroups.map(async (group) => {
            const groupConfig = form.config.byGroup[group.name] ?? form.config.default;
            const block = await setGroupConfiguration(
              contestId,
              group.id,
              formConfigToBlockRequest(groupConfig)
            );
            await syncWildcards(block.id, groupConfig.wildcards);
          })
        );
      }
      return true;
    } catch (err) {
      setApiError(
        err instanceof Error ? err.message : "Failed to save configuration."
      );
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = async () => {
    setApiError(null);

    if (step === 2) {
      const created = await handleCreateContest();
      if (!created) return;
    }

    if (step === 3) {
      const saved = await handleSaveConfiguration();
      if (!saved) return;
    }

    if (step !== 2 && step !== 3 && !validateStep(step)) {
      return;
    }

    setStep((s) => Math.min(s + 1, steps.length));
  };

  const handleBack = () => {
    setApiError(null);
    setStep((s) => Math.max(s - 1, 1));
  };

  const handlePublish = async () => {
    if (!contestId) {
      setApiError("Contest has not been created yet.");
      return;
    }

    setApiError(null);
    setIsLoading(true);

    try {
      await transitionLifecycle(contestId, { target_status: "PUBLISHED" });
      router.push("/org-admin/contests");
    } catch (err) {
      setApiError(
        err instanceof Error ? err.message : "Failed to publish contest."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const updateInfo = (info: ContestFormState["info"]) => {
    setForm((prev) => ({ ...prev, info }));
  };

  const updateStructure = (
    structure: ContestStructure,
    groups: string[]
  ) => {
    setForm((prev) => {
      let nextConfig = prev.config;
      if (structure === "GROUPED" && Object.keys(prev.config.byGroup).length === 0) {
        const byGroup: Record<string, ContestConfiguration> = {};
        groups.forEach((group) => {
          byGroup[group] = { ...prev.config.default };
        });
        nextConfig = { ...prev.config, byGroup };
      }
      return { ...prev, structure, groups, config: nextConfig };
    });
  };

  const updateConfig = (config: ContestFormState["config"]) => {
    setForm((prev) => ({ ...prev, config }));
  };

  const updateQuestions = (questions: ContestFormState["questions"]) => {
    setForm((prev) => ({ ...prev, questions }));
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link
          href="/org-admin/contests"
          className="flex items-center gap-1 hover:text-[#d94d1a]"
        >
          <ChevronLeft className="size-4" />
          Contests
        </Link>
        <span>/</span>
        <span className="font-medium text-slate-900">Create Contest</span>
      </div>

      <h2 className="text-2xl font-bold text-slate-900">Create Contest</h2>

      {/* Stepper */}
      <WizardStepper steps={steps} currentStep={step} />

      {apiError && (
        <Alert variant="destructive">
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      {/* Step content */}
      <div className="min-h-100">
        {step === 1 && (
          <ContestInfoStep
            data={form.info}
            onChange={updateInfo}
            errors={errors}
          />
        )}
        {step === 2 && (
          <StructureStep
            structure={form.structure}
            groups={form.groups}
            onChange={updateStructure}
            errors={errors}
          />
        )}
        {step === 3 && (
          <ConfigurationStep
            structure={form.structure}
            groups={form.groups}
            config={form.config}
            onChange={updateConfig}
            errors={errors}
          />
        )}
        {step === 4 && (
          <QuestionsStep
            structure={form.structure}
            groups={form.groups}
            questions={form.questions}
            onChange={updateQuestions}
          />
        )}
        {step === 5 && <ReviewStep data={form} contestId={contestId} />}
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={handleBack}
          disabled={step === 1 || isLoading}
          className={cn("gap-1.5", step === 1 && "invisible")}
        >
          <ChevronLeft className="size-4" />
          Back
        </Button>

        {step < steps.length ? (
          <Button
            type="button"
            onClick={handleNext}
            disabled={isLoading}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            {isLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <ChevronRight className="size-4" />
            )}
            {isLoading ? "Saving..." : "Continue"}
          </Button>
        ) : (
          <Button
            type="button"
            onClick={handlePublish}
            disabled={isLoading || !contestId}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            {isLoading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Publishing...
              </>
            ) : (
              <>
                <CheckCircle className="size-4" />
                Publish Contest
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
