"use client";
import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/jobs": "Jobs",
  "/applications": "Applications",
  "/outreach": "Outreach",
  "/inbox": "Inbox",
  "/settings": "Settings",
};

export function Header() {
  const pathname = usePathname();
  const title = Object.entries(titles).find(([k]) => pathname.startsWith(k))?.[1] ?? "AI Job Search";

  return (
    <header className="h-14 flex items-center border-b bg-background px-6">
      <h1 className="text-lg font-semibold">{title}</h1>
    </header>
  );
}
