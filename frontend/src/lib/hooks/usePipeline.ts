import useSWR from "swr";
import { fetchPipelineStatus } from "@/lib/api";

export function usePipelineStatus() {
  return useSWR("pipelines/status", fetchPipelineStatus, {
    refreshInterval: 10_000,
  });
}
