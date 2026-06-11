import useSWR from "swr";
import { fetchInbox } from "@/lib/api";
import type { EmailClassification } from "@/types";

export function useInbox(params?: { classification?: EmailClassification; page?: number }) {
  return useSWR(["inbox", params], () => fetchInbox(params));
}
