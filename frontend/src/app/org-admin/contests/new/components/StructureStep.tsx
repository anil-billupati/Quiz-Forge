"use client";

import { Trophy, Layers, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { ContestStructure } from "../types";

interface StructureStepProps {
  structure: ContestStructure;
  groups: string[];
  onChange: (structure: ContestStructure, groups: string[]) => void;
  errors: Record<string, string>;
}

const options: {
  value: ContestStructure;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  {
    value: "NORMAL",
    label: "Normal",
    description: "All participants compete together in one unified leaderboard.",
    icon: Trophy,
  },
  {
    value: "GROUPED",
    label: "Grouped",
    description: "Participants are divided into groups with separate sub-leaderboards.",
    icon: Layers,
  },
];

export default function StructureStep({
  structure,
  groups,
  onChange,
  errors,
}: StructureStepProps) {
  const handleSelect = (value: ContestStructure) => {
    if (value === "GROUPED" && groups.length === 0) {
      onChange(value, ["Group A", "Group B"]);
    } else {
      onChange(value, groups);
    }
  };

  const addGroup = () => {
    const nextLetter = String.fromCharCode(65 + groups.length);
    onChange(structure, [...groups, `Group ${nextLetter}`]);
  };

  const removeGroup = (index: number) => {
    if (groups.length <= 2) return;
    const next = [...groups];
    next.splice(index, 1);
    onChange(structure, next);
  };

  const renameGroup = (index: number, name: string) => {
    const next = [...groups];
    next[index] = name;
    onChange(structure, next);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="mb-2 text-lg font-semibold text-slate-900">
          Select Contest Structure
        </h3>
        <p className="mb-6 text-sm text-slate-500">
          Choose how your contest is organized.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          {options.map((option) => {
            const Icon = option.icon;
            const selected = structure === option.value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => handleSelect(option.value)}
                className={cn(
                  "flex flex-col items-start gap-3 rounded-xl border p-5 text-left transition-colors",
                  selected
                    ? "border-[#f05a22] bg-[#f05a22]/5"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    selected ? "bg-[#f05a22] text-white" : "bg-slate-100 text-slate-500"
                  )}
                >
                  <Icon className="size-5" />
                </div>
                <div>
                  <p className="font-semibold text-slate-900">{option.label}</p>
                  <p className="text-sm text-slate-500">{option.description}</p>
                </div>
                {selected && (
                  <p className="text-sm font-medium text-[#d94d1a]">✓ Selected</p>
                )}
              </button>
            );
          })}
        </div>
        {errors.structure && (
          <p className="mt-4 text-sm text-red-600">{errors.structure}</p>
        )}
      </div>

      {structure === "GROUPED" && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Groups</h3>
              <p className="text-sm text-slate-500">
                Define the groups for this contest.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addGroup}
              className="gap-1.5"
            >
              <Plus className="size-4" />
              Add Group
            </Button>
          </div>

          <div className="space-y-3">
            {groups.map((group, index) => (
              <div key={index} className="flex items-center gap-3">
                <Input
                  value={group}
                  onChange={(e) => renameGroup(index, e.target.value)}
                  placeholder="Group name"
                  className="flex-1 rounded-xl border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:border-[#f05a22] focus:ring-3 focus:ring-[#f05a22]/10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeGroup(index)}
                  disabled={groups.length <= 2}
                  className="text-slate-400 hover:text-red-600 disabled:opacity-30"
                  aria-label="Remove group"
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            ))}
          </div>
          {errors.groups && (
            <p className="mt-4 text-sm text-red-600">{errors.groups}</p>
          )}
        </div>
      )}
    </div>
  );
}
