"use client";
import { useState } from "react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScoreBadge } from "./ScoreBadge";
import { useJobs } from "@/lib/hooks/useJobs";
import { formatDate } from "@/lib/utils";
import type { JobStatus } from "@/types";
import { ExternalLink, ChevronLeft, ChevronRight } from "lucide-react";

const STATUS_COLORS: Record<JobStatus, "default" | "success" | "warning" | "error" | "secondary" | "outline"> = {
  discovered: "secondary",
  scored: "outline",
  pending_approval: "warning",
  approved: "success",
  rejected: "error",
  applied: "success",
  failed: "error",
};

interface Props {
  source?: string;
  status?: JobStatus;
  minScore?: number;
}

export function JobTable({ source, status, minScore = 0 }: Props) {
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 15;

  const { data: jobs, isLoading } = useJobs({ source, status, min_score: minScore, page });

  if (isLoading) {
    return <div className="py-10 text-center text-sm text-muted-foreground">Loading jobs…</div>;
  }

  const items = jobs ?? [];

  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Title</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Date</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                No jobs found
              </TableCell>
            </TableRow>
          )}
          {items.map((job) => (
            <TableRow key={job.id}>
              <TableCell className="font-medium max-w-[180px] truncate">{job.title}</TableCell>
              <TableCell>{job.company}</TableCell>
              <TableCell className="text-sm text-muted-foreground">{job.location ?? "—"}</TableCell>
              <TableCell>
                <Badge variant="outline" className="text-xs capitalize">{job.source ?? "—"}</Badge>
              </TableCell>
              <TableCell>
                <ScoreBadge score={job.composite_score} />
              </TableCell>
              <TableCell>
                <Badge variant={STATUS_COLORS[job.status]} className="capitalize text-xs">
                  {job.status.replace("_", " ")}
                </Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">{formatDate(job.created_at)}</TableCell>
              <TableCell>
                {job.url && (
                  <a href={job.url} target="_blank" rel="noopener noreferrer">
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
                  </a>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between px-1">
        <p className="text-xs text-muted-foreground">Page {page}</p>
        <div className="flex gap-1">
          <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => setPage((p) => p + 1)} disabled={items.length < PAGE_SIZE}>
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
