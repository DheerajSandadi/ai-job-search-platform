import axios from "axios";
import type {
  Job,
  Application,
  Outreach,
  InboxEmail,
  AnalyticsDay,
  PipelineRun,
  PipelineStatusResponse,
  Settings,
  JobStatus,
  ApplicationStatus,
  OutreachStatus,
  OutreachChannel,
  EmailClassification,
} from "@/types";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001",
});

const BASE = "/api/v1";

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export async function fetchJobs(params?: {
  source?: string;
  status?: JobStatus;
  min_score?: number;
  page?: number;
  page_size?: number;
}): Promise<Job[]> {
  const res = await api.get<Job[]>(`${BASE}/jobs`, { params });
  return res.data;
}

export async function fetchJob(id: string): Promise<Job> {
  const res = await api.get<Job>(`${BASE}/jobs/${id}`);
  return res.data;
}

// ─── Applications ─────────────────────────────────────────────────────────────

export async function fetchApplications(params?: {
  status?: ApplicationStatus;
  page?: number;
  page_size?: number;
}): Promise<Application[]> {
  const res = await api.get<Application[]>(`${BASE}/applications`, { params });
  return res.data;
}

export async function fetchPendingApplications(): Promise<Application[]> {
  const res = await api.get<Application[]>(`${BASE}/applications/pending`);
  return res.data;
}

export async function approveApplication(id: string): Promise<{
  message: string;
  id: string;
  job_url: string | null;
  job_title: string | null;
  company: string | null;
}> {
  const res = await api.post(`${BASE}/applications/${id}/approve`);
  return res.data;
}

export async function rejectApplication(id: string): Promise<{ message: string; id: string }> {
  const res = await api.post(`${BASE}/applications/${id}/reject`);
  return res.data;
}

export async function markApplied(id: string): Promise<{ message: string; id: string; applied_at: string }> {
  const res = await api.post(`${BASE}/applications/${id}/mark-applied`);
  return res.data;
}

// ─── Outreach ─────────────────────────────────────────────────────────────────

export async function fetchOutreach(params?: {
  status?: OutreachStatus;
  channel?: OutreachChannel;
  page?: number;
  page_size?: number;
}): Promise<Outreach[]> {
  const res = await api.get<Outreach[]>(`${BASE}/outreach`, { params });
  return res.data;
}

// ─── Inbox ────────────────────────────────────────────────────────────────────

export async function getInbox(
  classification?: string,
  days?: number,
  limit = 100,
  offset = 0,
): Promise<InboxEmail[]> {
  const params: Record<string, string | number> = { limit, offset }
  if (classification) params.classification = classification
  if (days) params.days = days
  const res = await api.get<InboxEmail[]>(`${BASE}/inbox`, { params })
  return res.data
}

export async function getEmailThreads(stage?: string, days = 30) {
  const params: Record<string, string | number> = { days }
  if (stage) params.stage = stage
  const res = await api.get(`${BASE}/inbox/threads`, { params })
  return res.data
}

/** @deprecated use getInbox */
export const fetchInbox = (params?: { classification?: EmailClassification; page?: number }) =>
  getInbox(params?.classification)

// ─── Analytics ────────────────────────────────────────────────────────────────

export async function fetchTodayAnalytics(): Promise<AnalyticsDay> {
  const res = await api.get<AnalyticsDay>(`${BASE}/analytics/today`);
  return res.data;
}

export async function fetchAnalyticsHistory(days = 7): Promise<AnalyticsDay[]> {
  const res = await api.get<AnalyticsDay[]>(`${BASE}/analytics/history`, {
    params: { days },
  });
  return res.data;
}

// ─── Pipelines ────────────────────────────────────────────────────────────────

export async function fetchPipelineStatus(): Promise<PipelineStatusResponse> {
  const res = await api.get<PipelineStatusResponse>(`${BASE}/pipelines/status`);
  return res.data;
}

export async function triggerMorningPipeline(): Promise<PipelineRun> {
  const res = await api.post<PipelineRun>(`${BASE}/pipelines/morning/trigger`);
  return res.data;
}

export async function triggerRetryPipeline(): Promise<PipelineRun> {
  const res = await api.post<PipelineRun>(`${BASE}/pipelines/retry/trigger`);
  return res.data;
}

// ─── Settings ─────────────────────────────────────────────────────────────────

export async function fetchSettings(): Promise<Settings> {
  const res = await api.get<Settings>(`${BASE}/settings`);
  return res.data;
}

export async function updateSettings(body: Settings): Promise<Settings> {
  const res = await api.put<Settings>(`${BASE}/settings`, body);
  return res.data;
}

export default api;
