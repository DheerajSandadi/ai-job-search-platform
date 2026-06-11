import useSWR from "swr";
import { fetchTodayAnalytics, fetchAnalyticsHistory } from "@/lib/api";

export function useTodayAnalytics() {
  return useSWR("analytics/today", fetchTodayAnalytics);
}

export function useAnalyticsHistory(days = 7) {
  return useSWR(["analytics/history", days], () => fetchAnalyticsHistory(days));
}
