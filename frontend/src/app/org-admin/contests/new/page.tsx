"use client";

import { useEffect, useMemo, useState } from "react";
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
import { assignContestModerators } from "@/lib/api/moderators";
import { formConfigToBlockRequest } from "@/lib/contest-config";
import WizardStepper from "./components/WizardStepper";
import ContestInfoStep from "./components/ContestInfoStep";
import StructureStep from "./components/StructureStep";
import ConfigurationStep from "./components/ConfigurationStep";
import ModeratorsStep from "./components/ModeratorsStep";
import QuestionsStep from "./components/QuestionsStep";
import ReviewStep from "./components/ReviewStep";
import {
  type ContestFormState,
  type ContestStructure,
  type ContestConfiguration,
  defaultConfiguration,
} from "./types";

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
    moderators: [],
    newModeratorIds: [],
    questions: [],
  };
}

function requiresModeratorControlled(form: ContestFormState): boolean {
  return (
    form.config.default.revealMode === "MODERATOR_CONTROLLED" ||
    (form.structure === "GROUPED" &&
      Object.values(form.config.byGroup).some(
        (c) => c.revealMode === "MODERATOR_CONTROLLED"
      ))
  );
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

  const steps = useMemo(() => {
    const list = ["Contest Info", "Structure", "Configuration"];
    if (requiresModeratorControlled(form)) {
      list.push("Moderators");
    }
    list.push("Questions", "Review & Publish");
    return list;
  }, [form]);

  const currentLabel = steps[step - 1];

  // Keep the current step in bounds when the visible step list changes
  // (e.g., switching reveal mode from Moderator Controlled to Automatic).
  useEffect(() => {
    setStep((s) => Math.min(s, steps.length));
  }, [steps.length]);

  const validateStep = (currentStep: number): boolean => {
    const label = steps[currentStep - 1];
    const nextErrors: Record<string, string> = {};

    if (label === "Contest Info") {
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

    if (label === "Structure") {
      if (form.structure === "GROUPED") {
        if (form.groups.length < 2) {
          nextErrors.groups = "At least two groups are required";
        }
        if (form.groups.some((g) => !g.trim())) {
          nextErrors.groups = "Group names cannot be empty";
        }
      }
    }

    if (label === "Moderators" && requiresModeratorControlled(form)) {
      if (form.moderators.length === 0) {
        nextErrors.moderators =
          "At least one moderator is required for Moderator Controlled reveal mode.";
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

  const handleAssignModerators = async (): Promise<boolean> => {
    if (!validateStep(step)) return false;
    if (!contestId) {
      setApiError("Contest has not been created yet.");
      return false;
    }

    setIsLoading(true);
    setApiError(null);

    try {
      // TODO: replace stub with real API when backend supports contest-level
      // moderator assignment.
      await assignContestModerators(
        contestId,
        form.moderators.map((m) => m.id)
      );
      return true;
    } catch (err) {
      setApiError(
        err instanceof Error ? err.message : "Failed to assign moderators."
      );
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = async () => {
    setApiError(null);

    if (currentLabel === "Structure") {
      const created = await handleCreateContest();
      if (!created) return;
    }

    if (currentLabel === "Configuration") {
      const saved = await handleSaveConfiguration();
      if (!saved) return;
    }

    if (currentLabel === "Moderators") {
      const assigned = await handleAssignModerators();
      if (!assigned) return;
    }

    if (
      !["Structure", "Configuration", "Moderators"].includes(currentLabel) &&
      !validateStep(step)
    ) {
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

    if (requiresModeratorControlled(form) && form.moderators.length === 0) {
      setApiError(
        "At least one moderator is required for Moderator Controlled reveal mode before publishing."
      );
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

  const updateModerators = (
    moderators: ContestFormState["moderators"],
    newModeratorIds: ContestFormState["newModeratorIds"]
  ) => {
    setForm((prev) => ({ ...prev, moderators, newModeratorIds }));
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
        {currentLabel === "Contest Info" && (
          <ContestInfoStep
            data={form.info}
            onChange={updateInfo}
            errors={errors}
          />
        )}
        {currentLabel === "Structure" && (
          <StructureStep
            structure={form.structure}
            groups={form.groups}
            onChange={updateStructure}
            errors={errors}
          />
        )}
        {currentLabel === "Configuration" && (
          <ConfigurationStep
            structure={form.structure}
            groups={form.groups}
            config={form.config}
            onChange={updateConfig}
            errors={errors}
          />
        )}
        {currentLabel === "Moderators" && (
          <ModeratorsStep
            revealMode={form.config.default.revealMode}
            selected={form.moderators}
            newModeratorIds={form.newModeratorIds}
            errors={errors}
            onChange={updateModerators}
          />
        )}
        {currentLabel === "Questions" && (
          <QuestionsStep
            structure={form.structure}
            groups={form.groups}
            questions={form.questions}
            onChange={updateQuestions}
          />
        )}
        {currentLabel === "Review & Publish" && (
          <ReviewStep data={form} contestId={contestId} />
        )}
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
