import useSWR from "swr";
import { getInbox, getEmailThreads } from "@/lib/api";

export function useInbox(classification?: string, days?: number) {
  return useSWR(
    ["inbox", classification, days],
    () => getInbox(classification, days),
    { refreshInterval: 30000, revalidateOnFocus: true },
  );
}

export function useEmailThreads(stage?: string, days = 30) {
  return useSWR(
    ["inbox/threads", stage, days],
    () => getEmailThreads(stage, days),
    { refreshInterval: 30000, revalidateOnFocus: true },
  );
}
