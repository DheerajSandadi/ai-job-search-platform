"use client";
import { useState } from "react";
import { Play, RotateCcw, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { usePipelineStatus } from "@/lib/hooks/usePipeline";
import { triggerMorningPipeline, triggerRetryPipeline } from "@/lib/api";
import type { PipelineRunStatus } from "@/types";

function StatusDot({ status }: { status: PipelineRunStatus }) {
  if (status === "running")   return <Loader2 size={14} className="animate-spin" style={{ color: "#5B7FFF" }} />;
  if (status === "completed") return <CheckCircle2 size={14} style={{ color: "#22C55E" }} />;
  if (status === "failed")    return <XCircle size={14} style={{ color: "#EF4444" }} />;
  return <Clock size={14} style={{ color: "var(--color-text-muted)" }} />;
}

export function PipelineStatus() {
  const { data, mutate } = usePipelineStatus();
  const [loading, setLoading] = useState<string | null>(null);

  async function trigger(type: "morning" | "retry") {
    setLoading(type);
    try {
      if (type === "morning") await triggerMorningPipeline();
      else await triggerRetryPipeline();
      await mutate();
    } finally {
      setLoading(null);
    }
  }

  const pipelines = [
    { key: "morning" as const, label: "Morning Pipeline", run: data?.morning, icon: Play },
    { key: "retry"   as const, label: "Retry Pipeline",   run: data?.retry,   icon: RotateCcw },
  ];

  return (
    <div className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-primary)" }}>
        Pipeline Status
      </p>

      {pipelines.map(({ key, label, run, icon: Icon }) => (
        <div key={key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <StatusDot status={run?.status ?? "idle"} />
            <div>
              <p style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)" }}>{label}</p>
              <p style={{ fontSize: 11, color: "var(--color-text-muted)", textTransform: "capitalize" }}>
                {run?.status ?? "idle"}
                {run?.stats && Object.keys(run.stats).length > 0 && ` · ${(run.stats as Record<string, number>)["jobs_found"] ?? 0} jobs`}
              </p>
            </div>
          </div>
          <button
            className="btn-outline"
            style={{ padding: "5px 12px", fontSize: 12, gap: 5 }}
            onClick={() => trigger(key)}
            disabled={loading === key || run?.status === "running"}
          >
            {loading === key
              ? <Loader2 size={12} className="animate-spin" />
              : <Icon size={12} strokeWidth={2} />}
            Run
          </button>
        </div>
      ))}
    </div>
  );
}
