import type { ReactNode } from "react";

export const metadata = {
  title: "ContestForge",
  description: "Multi-tenant live contest engine",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
