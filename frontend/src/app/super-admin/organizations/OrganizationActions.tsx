"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { MoreHorizontal, Pencil, Power, PowerOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  updateOrganization,
  updateOrganizationStatus,
} from "./actions";

interface OrganizationActionsProps {
  organization: {
    id: string;
    name: string;
    status: "active" | "suspended";
    custom_domain?: string | null;
  };
}

export default function OrganizationActions({
  organization,
}: OrganizationActionsProps) {
  const router = useRouter();

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="size-8">
              <MoreHorizontal className="size-4" />
              <span className="sr-only">Manage {organization.name}</span>
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent side="left">
          <p>Manage organization</p>
        </TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-44">
        <EditDialog organization={organization} onSuccess={() => router.refresh()} />
        <StatusDialog organization={organization} onSuccess={() => router.refresh()} />
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function EditDialog({
  organization,
  onSuccess,
}: {
  organization: OrganizationActionsProps["organization"];
  onSuccess: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState(organization.name);
  const [customDomain, setCustomDomain] = useState(
    organization.custom_domain ?? ""
  );

  function handleSubmit(formData: FormData) {
    setError(null);
    startTransition(async () => {
      try {
        await updateOrganization(organization.id, {
          name: String(formData.get("name")),
          custom_domain: String(formData.get("custom_domain")),
        });
        setOpen(false);
        onSuccess();
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to update organization."
        );
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
          <Pencil className="size-4" />
          Edit
        </DropdownMenuItem>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Organization</DialogTitle>
          <DialogDescription>
            Update the organization name and custom domain.
          </DialogDescription>
        </DialogHeader>
        <form action={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor={`name-${organization.id}`}>Name</Label>
            <Input
              id={`name-${organization.id}`}
              name="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Organization name"
              required
              disabled={isPending}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`domain-${organization.id}`}>Custom domain</Label>
            <Input
              id={`domain-${organization.id}`}
              name="custom_domain"
              value={customDomain}
              onChange={(e) => setCustomDomain(e.target.value)}
              placeholder="contests.example.com"
              disabled={isPending}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isPending || !name.trim()}
              className="bg-[#f05a22] hover:bg-[#d94d1a]"
            >
              {isPending ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function StatusDialog({
  organization,
  onSuccess,
}: {
  organization: OrganizationActionsProps["organization"];
  onSuccess: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const isSuspended = organization.status === "suspended";
  const actionLabel = isSuspended ? "Activate" : "Suspend";
  const nextStatus = isSuspended ? "ACTIVE" : "SUSPENDED";

  function handleConfirm() {
    setError(null);
    startTransition(async () => {
      try {
        await updateOrganizationStatus(organization.id, nextStatus);
        setOpen(false);
        onSuccess();
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : `Failed to ${actionLabel.toLowerCase()} organization.`
        );
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <DropdownMenuItem
          onSelect={(e) => e.preventDefault()}
          className={isSuspended ? "text-emerald-600" : "text-destructive"}
        >
          {isSuspended ? (
            <Power className="size-4" />
          ) : (
            <PowerOff className="size-4" />
          )}
          {actionLabel}
        </DropdownMenuItem>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {actionLabel} {organization.name}?
          </DialogTitle>
          <DialogDescription>
            {isSuspended
              ? "This organization will be reactivated and able to use the platform again."
              : "This organization will be suspended and unable to access the platform until reactivated."}
          </DialogDescription>
        </DialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isPending}
            variant={isSuspended ? "default" : "destructive"}
            className={isSuspended ? "bg-emerald-600 hover:bg-emerald-700" : ""}
          >
            {isPending ? "Processing..." : actionLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
