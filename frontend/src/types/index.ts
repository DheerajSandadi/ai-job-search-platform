// ─── Enums ────────────────────────────────────────────────────────────────────

export type JobStatus =
  | "discovered"
  | "scored"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "applied"
  | "failed";

export type ApplicationStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "applied"
  | "submitted"
  | "failed";

export type OutreachStatus = "queued" | "sent" | "replied" | "bounced" | "opt_out";
export type OutreachChannel = "email" | "linkedin";

export type EmailClassification =
  | "recruiter_reply"
  | "interview_invite"
  | "rejection"
  | "offer"
  | "follow_up_needed"
  | "unrelated";

export type PipelineType = "morning" | "inbox" | "retry";
export type PipelineRunStatus = "running" | "completed" | "failed" | "idle";

// ─── Job ──────────────────────────────────────────────────────────────────────

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string | null;
  url: string | null;
  description: string | null;
  source: string | null;
  ats_score: number | null;
  relevance_score: number | null;
  composite_score: number | null;
  status: JobStatus;
  raw_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface JobCreate {
  title: string;
  company: string;
  location?: string;
  url?: string;
  description?: string;
  source?: string;
  ats_score?: number;
  relevance_score?: number;
  composite_score?: number;
  status?: JobStatus;
}

// ─── Resume ───────────────────────────────────────────────────────────────────

export interface Resume {
  id: string;
  job_id: string;
  original_text: string;
  tailored_text: string;
  diff_summary: string | null;
  ats_score: number | null;
  keywords_added: string[];
  created_at: string;
}

// ─── Application ──────────────────────────────────────────────────────────────

export interface Application {
  id: string;
  job_id: string;
  resume_id: string | null;
  status: ApplicationStatus;
  cover_letter: string | null;
  applied_at: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  job: Job | null;
  resume: Resume | null;
}

// ─── Recruiter ────────────────────────────────────────────────────────────────

export interface Recruiter {
  id: string;
  name: string;
  email: string | null;
  linkedin_url: string | null;
  company: string | null;
  title: string | null;
  source: string | null;
  created_at: string;
}

// ─── Outreach ─────────────────────────────────────────────────────────────────

export interface Outreach {
  id: string;
  recruiter_id: string;
  job_id: string | null;
  channel: OutreachChannel;
  subject: string | null;
  body: string;
  status: OutreachStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  replied_at: string | null;
  created_at: string;
  recruiter: Recruiter | null;
}

// ─── Inbox ────────────────────────────────────────────────────────────────────

export interface InboxEmail {
  id: string;
  gmail_message_id: string | null;
  thread_id: string | null;
  sender_email: string;
  sender_name: string | null;
  subject: string | null;
  body_preview: string | null;
  full_body: string | null;
  received_at: string;
  classification: EmailClassification | null;
  pipeline_stage: string | null;
  draft_reply: string | null;
  company_name: string | null;
  role_title: string | null;
  reply_sent: boolean;
  reply_sent_at: string | null;
  labels: string[];
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export interface AnalyticsDay {
  date: string;
  jobs_discovered: number;
  jobs_scored: number;
  applications_submitted: number;
  applications_failed: number;
  recruiters_contacted: number;
  recruiter_replies: number;
  interviews_scheduled: number;
}

// ─── Pipeline ─────────────────────────────────────────────────────────────────

export interface PipelineRun {
  id: string | null;
  pipeline_type: PipelineType;
  status: PipelineRunStatus;
  started_at: string | null;
  completed_at: string | null;
  stats: Record<string, unknown>;
  errors: string[];
}

export interface PipelineStatusResponse {
  morning: PipelineRun;
  retry: PipelineRun;
  inbox: PipelineRun;
}

// ─── Settings ─────────────────────────────────────────────────────────────────

export interface Settings {
  ats_confidence_threshold: number;
  morning_pipeline_cron: string;
  retry_pipeline_cron: string;
  auto_apply_enabled: boolean;
  max_applications_per_day: number;
  target_roles: string[];
  excluded_companies: string[];
  anthropic_key_configured: boolean;
  supabase_configured: boolean;
  gmail_configured: boolean;
}
