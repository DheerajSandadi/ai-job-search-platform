import { Briefcase, FileCheck, MessageSquare, CalendarCheck } from "lucide-react";
import type { AnalyticsDay } from "@/types";

interface Props { data: AnalyticsDay | undefined; }

const STATS = [
  { key: "jobs_discovered",       label: "Jobs Discovered",    icon: Briefcase,      color: "#5B7FFF" },
  { key: "applications_submitted",label: "Applications Sent",  icon: FileCheck,      color: "#22C55E" },
  { key: "recruiter_replies",     label: "Recruiter Replies",  icon: MessageSquare,  color: "#A78BFA" },
  { key: "interviews_scheduled",  label: "Interviews",         icon: CalendarCheck,  color: "#F59E0B" },
] as const;

export function StatsCards({ data }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {STATS.map(({ key, label, icon: Icon, color }) => (
        <div key={key} className="card" style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 20 }}>
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              background: `${color}15`,
            }}
          >
            <Icon size={17} style={{ color }} strokeWidth={1.8} />
          </div>
          <div>
            <p style={{ fontSize: 22, fontWeight: 600, color: "var(--color-text-primary)", lineHeight: 1 }}>
              {data?.[key] ?? 0}
            </p>
            <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 3 }}>{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
