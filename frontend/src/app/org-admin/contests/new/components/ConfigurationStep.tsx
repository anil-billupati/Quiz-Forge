"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ConfigurationForm from "./ConfigurationForm";
import type { ContestFormState } from "../types";

interface ConfigurationStepProps {
  structure: ContestFormState["structure"];
  groups: string[];
  config: ContestFormState["config"];
  onChange: (config: ContestFormState["config"]) => void;
  errors: Record<string, string>;
}

export default function ConfigurationStep({
  structure,
  groups,
  config,
  onChange,
}: ConfigurationStepProps) {
  if (structure === "NORMAL") {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="mb-6 text-lg font-semibold text-slate-900">
          Contest Configuration
        </h3>
        <ConfigurationForm
          config={config.default}
          onChange={(next) => onChange({ ...config, default: next })}
        />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <h3 className="mb-6 text-lg font-semibold text-slate-900">
        Contest Configuration
      </h3>
      <p className="mb-4 text-sm text-slate-500">
        Configure settings for each group.
      </p>

      <Tabs defaultValue={groups[0]} className="w-full">
        <TabsList className="mb-4 w-full justify-start bg-slate-100">
          {groups.map((group) => (
            <TabsTrigger
              key={group}
              value={group}
              className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white"
            >
              {group}
            </TabsTrigger>
          ))}
        </TabsList>
        {groups.map((group) => (
          <TabsContent key={group} value={group}>
            <ConfigurationForm
              config={config.byGroup[group] ?? config.default}
              onChange={(next) =>
                onChange({
                  ...config,
                  byGroup: { ...config.byGroup, [group]: next },
                })
              }
            />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
