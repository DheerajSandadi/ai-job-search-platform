import useSWR from "swr";
import { fetchOutreach } from "@/lib/api";
import type { OutreachStatus, OutreachChannel } from "@/types";

export function useOutreach(params?: {
  status?: OutreachStatus;
  channel?: OutreachChannel;
  page?: number;
}) {
  return useSWR(["outreach", params], () => fetchOutreach(params));
}
