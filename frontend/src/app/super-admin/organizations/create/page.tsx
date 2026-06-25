import type { Metadata } from "next";
import CreateOrganizationForm from "./CreateOrganizationForm";

export const metadata: Metadata = {
  title: "Create Organization",
  description: "Create a new organization workspace in ContestForge.",
  alternates: { canonical: "/super-admin/organizations/create" },
  robots: { index: false, follow: false },
};

export default function CreateOrganizationPage() {
  return <CreateOrganizationForm />;
}
