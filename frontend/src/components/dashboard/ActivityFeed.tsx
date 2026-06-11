"use client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { AnalyticsDay } from "@/types";

interface Props { data: AnalyticsDay[] | undefined; }

export function ActivityFeed({ data }: Props) {
  const chartData = (data ?? []).map((d) => ({
    date: d.date.slice(5),
    Applications: d.applications_submitted,
    Replies: d.recruiter_replies,
    Interviews: d.interviews_scheduled,
  }));

  return (
    <div className="card" style={{ padding: 20 }}>
      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-primary)", marginBottom: 20 }}>
        7-Day Activity
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 0, right: 0, left: -24, bottom: 0 }} barSize={6} barGap={3}>
          <CartesianGrid vertical={false} stroke="var(--color-border)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "var(--color-text-muted)" as string }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--color-text-muted)" as string }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-card)",
              border: "0.5px solid var(--color-border)",
              borderRadius: 8,
              fontSize: 12,
              boxShadow: "none",
            }}
            cursor={{ fill: "rgba(0,0,0,0.03)" }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
            iconType="circle"
            iconSize={6}
          />
          <Bar dataKey="Applications" fill="#5B7FFF" radius={[3, 3, 0, 0]} />
          <Bar dataKey="Replies"      fill="#22C55E" radius={[3, 3, 0, 0]} />
          <Bar dataKey="Interviews"   fill="#F59E0B" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
