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
  auth: {
    username: process.env.NEXT_PUBLIC_API_USERNAME ?? "admin",
    password: process.env.NEXT_PUBLIC_API_PASSWORD ?? "jobpilot",
  },
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

export async function updateThreadStage(threadId: string, stage: string) {
  const res = await api.patch(`${BASE}/inbox/threads/${threadId}/stage`, { stage })
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

export async function triggerInboxPipeline(): Promise<PipelineRun> {
  const res = await api.post<PipelineRun>(`${BASE}/pipelines/inbox/trigger`);
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

export async function sendReply(emailId: string): Promise<{ message: string; email_id: string; sent_at: string }> {
  const res = await api.post(`${BASE}/inbox/${emailId}/send-reply`)
  return res.data
}

// ─── Gmail Tracker ────────────────────────────────────────────────────────────

export const getTrackerClassifyStatus = () =>
  api.get(`${BASE}/tracker/classify/status`).then(r => r.data)

export const startTrackerClassification = () =>
  api.post(`${BASE}/tracker/classify`).then(r => r.data)

export const getTrackerDashboardOverview = () =>
  api.get(`${BASE}/tracker/dashboard/overview`).then(r => r.data)

export const getTrackerActivity = (days = 30) =>
  api.get(`${BASE}/tracker/dashboard/activity`, { params: { days } }).then(r => r.data)

export const getTrackerTopCompanies = () =>
  api.get(`${BASE}/tracker/dashboard/top-companies`).then(r => r.data)

export const getTrackerEmailStats = () =>
  api.get(`${BASE}/tracker/dashboard/email-stats`).then(r => r.data)

export const getTrackerApplications = (params: Record<string, unknown> = {}) =>
  api.get(`${BASE}/tracker/applications`, { params }).then(r => r.data)

export const createTrackerApplication = (data: {
  company_name: string; role_title: string; status?: string;
  applied_date?: string; job_url?: string; notes?: string;
}) => api.post(`${BASE}/tracker/applications`, data).then(r => r.data)

export const updateTrackerApplicationStatus = (id: string, status: string) =>
  api.patch(`${BASE}/tracker/applications/${id}/status`, null, { params: { status } }).then(r => r.data)

export const updateTrackerApplication = (id: string, data: Record<string, unknown>) =>
  api.patch(`${BASE}/tracker/applications/${id}`, data).then(r => r.data)

export const deleteTrackerApplication = (id: string) =>
  api.delete(`${BASE}/tracker/applications/${id}`).then(r => r.data)

export const getTrackerApplicationEmails = (id: string) =>
  api.get(`${BASE}/tracker/applications/${id}/emails`).then(r => r.data)

export const getTrackerFollowupDraft = (emailId: string) =>
  api.get(`${BASE}/tracker/emails/${emailId}/followup-draft`).then(r => r.data)

export const sendTrackerFollowup = (emailId: string, body: string, subject?: string) =>
  api.post(`${BASE}/tracker/emails/${emailId}/send-followup`, { body, subject }).then(r => r.data)

export const syncTrackerGmail = () =>
  api.post(`${BASE}/tracker/gmail/sync`).then(r => r.data)

export default api;
