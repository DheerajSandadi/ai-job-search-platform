import useSWR from "swr";
import { fetchApplications, fetchPendingApplications } from "@/lib/api";
import type { ApplicationStatus } from "@/types";

export function useApplications(params?: { status?: ApplicationStatus; page?: number }) {
  return useSWR(["applications", params], () => fetchApplications(params));
}

export function usePendingApplications() {
  return useSWR("applications/pending", fetchPendingApplications);
}
