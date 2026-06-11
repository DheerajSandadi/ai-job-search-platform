import useSWR from "swr";
import { fetchJobs, fetchJob } from "@/lib/api";
import type { JobStatus } from "@/types";

export function useJobs(params?: {
  source?: string;
  status?: JobStatus;
  min_score?: number;
  page?: number;
}) {
  return useSWR(["jobs", params], () => fetchJobs(params));
}

export function useJob(id: string) {
  return useSWR(id ? ["job", id] : null, () => fetchJob(id));
}
