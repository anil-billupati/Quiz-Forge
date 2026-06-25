"use client";

import { useEffect, useState } from "react";
import { Loader2, Save, Trophy, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ContestOut } from "@/lib/api/contests";
import type { ConfigurationBlockResponse } from "@/lib/api/configurations";
import {
  getContestConfiguration,
  setContestConfiguration,
  getGroupConfiguration,
  setGroupConfiguration,
} from "@/lib/api/configurations";
import { listGroups, type GroupOut } from "@/lib/api/groups";
import { listWildcards, type WildcardConfig } from "@/lib/api/wildcards";
import { isDraft } from "@/lib/contest-status";
import { blockToFormConfig, formConfigToBlockRequest } from "@/lib/contest-config";
import ConfigurationForm from "../../new/components/ConfigurationForm";
import type { ContestConfiguration } from "../../new/types";
import WildcardEditor from "../components/WildcardEditor";

interface ConfigurationTabProps {
  contest: ContestOut;
}

type LoadState = "loading" | "error" | "ready";

interface BlockEntry {
  block: ConfigurationBlockResponse;
  wildcards: WildcardConfig[];
}

export default function ConfigurationTab({ contest }: ConfigurationTabProps) {
  const editable = isDraft(contest.lifecycle_status);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [apiError, setApiError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [normalBlock, setNormalBlock] = useState<BlockEntry | null>(null);
  const [normalConfig, setNormalConfig] = useState<ContestConfiguration | null>(null);

  const [groups, setGroups] = useState<GroupOut[]>([]);
  const [groupBlocks, setGroupBlocks] = useState<Record<string, BlockEntry>>({});
  const [groupConfigs, setGroupConfigs] = useState<Record<string, ContestConfiguration>>({});
  const [activeGroup, setActiveGroup] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoadState("loading");
      setApiError(null);

      try {
        if (contest.structure === "NORMAL") {
          const block = await getContestConfiguration(contest.id);
          const wildcards = await listWildcards(block.id);
          if (cancelled) return;
          setNormalBlock({ block, wildcards });
          setNormalConfig(blockToFormConfig(block));
        } else {
          const loadedGroups = await listGroups(contest.id);
          if (cancelled) return;
          setGroups(loadedGroups);

          if (loadedGroups.length > 0) {
            setActiveGroup(loadedGroups[0].id);
            const entries = await Promise.all(
              loadedGroups.map(async (group) => {
                const block = await getGroupConfiguration(contest.id, group.id);
                const wildcards = await listWildcards(block.id);
                return {
                  groupId: group.id,
                  entry: { block, wildcards },
                  config: blockToFormConfig(block),
                };
              })
            );
            if (cancelled) return;
            setGroupBlocks(
              Object.fromEntries(entries.map((e) => [e.groupId, e.entry]))
            );
            setGroupConfigs(
              Object.fromEntries(entries.map((e) => [e.groupId, e.config]))
            );
          }
        }
        setLoadState("ready");
      } catch (err) {
        if (cancelled) return;
        setApiError(err instanceof Error ? err.message : "Failed to load configuration.");
        setLoadState("error");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [contest.id, contest.structure]);

  const handleSaveNormal = async () => {
    if (!normalBlock || !normalConfig) return;
    setSaveError(null);
    setIsSaving(true);
    try {
      const block = await setContestConfiguration(
        contest.id,
        formConfigToBlockRequest(normalConfig)
      );
      const wildcards = await listWildcards(block.id);
      setNormalBlock({ block, wildcards });
      setNormalConfig(blockToFormConfig(block));
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save configuration.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveGroup = async (groupId: string) => {
    const config = groupConfigs[groupId];
    if (!config) return;
    setSaveError(null);
    setIsSaving(true);
    try {
      const block = await setGroupConfiguration(
        contest.id,
        groupId,
        formConfigToBlockRequest(config)
      );
      const wildcards = await listWildcards(block.id);
      setGroupBlocks((prev) => ({ ...prev, [groupId]: { block, wildcards } }));
      setGroupConfigs((prev) => ({ ...prev, [groupId]: blockToFormConfig(block) }));
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save configuration.");
    } finally {
      setIsSaving(false);
    }
  };

  if (loadState === "loading") {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white">
        <Loader2 className="size-6 animate-spin text-slate-400" />
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>
            {apiError ?? "Could not load configuration."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (contest.structure === "GROUPED" && groups.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
        <Trophy className="size-8 text-slate-400" />
        <h3 className="mt-4 text-lg font-semibold text-slate-900">No groups yet</h3>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          Create groups first to configure each group&apos;s settings.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Configuration</h3>
          <p className="text-sm text-slate-500">
            {editable
              ? "Edit how the contest is run and scored."
              : "Configuration is locked after the contest leaves Draft."}
          </p>
        </div>
        {editable && (
          <Button
            onClick={() =>
              contest.structure === "NORMAL"
                ? handleSaveNormal()
                : handleSaveGroup(activeGroup)
            }
            disabled={isSaving}
            className="gap-1.5 bg-[#f05a22] hover:bg-[#d94d1a]"
          >
            {isSaving && <Loader2 className="size-4 animate-spin" />}
            <Save className="size-4" />
            Save Configuration
          </Button>
        )}
      </div>

      {saveError && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{saveError}</AlertDescription>
        </Alert>
      )}

      {contest.structure === "NORMAL" && normalConfig && normalBlock && (
        <div className={editable ? "" : "pointer-events-none opacity-70"}>
          <ConfigurationForm
            config={normalConfig}
            onChange={editable ? setNormalConfig : () => {}}
          />
          <div className="mt-8 border-t border-slate-100 pt-6">
            <WildcardEditor
              configBlockId={normalBlock.block.id}
              wildcards={normalBlock.wildcards}
              editable={editable}
              onChange={(updated) =>
                setNormalBlock((prev) => (prev ? { ...prev, wildcards: updated } : prev))
              }
            />
          </div>
        </div>
      )}

      {contest.structure === "GROUPED" && groups.length > 0 && (
        <Tabs value={activeGroup} onValueChange={setActiveGroup}>
          <TabsList className="mb-4 w-full justify-start bg-slate-100">
            {groups.map((group) => (
              <TabsTrigger
                key={group.id}
                value={group.id}
                className="data-[state=active]:bg-[#f05a22] data-[state=active]:text-white"
              >
                {group.name}
              </TabsTrigger>
            ))}
          </TabsList>

          {groups.map((group) => {
            const config = groupConfigs[group.id];
            const entry = groupBlocks[group.id];
            return (
              <TabsContent key={group.id} value={group.id}>
                {config && entry ? (
                  <div className={editable ? "" : "pointer-events-none opacity-70"}>
                    <ConfigurationForm
                      config={config}
                      onChange={
                        editable
                          ? (next) =>
                              setGroupConfigs((prev) => ({
                                ...prev,
                                [group.id]: next,
                              }))
                          : () => {}
                      }
                    />
                    <div className="mt-8 border-t border-slate-100 pt-6">
                      <WildcardEditor
                        configBlockId={entry.block.id}
                        wildcards={entry.wildcards}
                        editable={editable}
                        onChange={(updated) =>
                          setGroupBlocks((prev) => ({
                            ...prev,
                            [group.id]: { ...entry, wildcards: updated },
                          }))
                        }
                      />
                    </div>
                  </div>
                ) : (
                  <div className="flex h-32 items-center justify-center">
                    <Loader2 className="size-5 animate-spin text-slate-400" />
                  </div>
                )}
              </TabsContent>
            );
          })}
        </Tabs>
      )}
    </div>
  );
}
