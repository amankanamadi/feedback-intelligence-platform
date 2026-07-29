export type FeedbackStatus = "New" | "Acknowledged" | "In Review" | "In Progress" | "Resolved" | "Closed";
export type Priority = "Low" | "Medium" | "High" | "Critical";
export type Sentiment = "Positive" | "Neutral" | "Negative";
export type MainCategory = "Incident" | "Service Request" | "General Feedback";
export type FeedbackSource =
  | "Web Form"
  | "In-App Widget"
  | "Mobile App"
  | "Email"
  | "API"
  | "Survey"
  | "Chatbot"
  | "QR Code";

export const STATUS_OPTIONS: FeedbackStatus[] = ["New", "Acknowledged", "In Review", "In Progress", "Resolved", "Closed"];
export const PRIORITY_OPTIONS: Priority[] = ["Low", "Medium", "High", "Critical"];
export const MAIN_CATEGORY_OPTIONS: MainCategory[] = ["Incident", "Service Request", "General Feedback"];
export const SENTIMENT_OPTIONS: Sentiment[] = ["Positive", "Neutral", "Negative"];

export type Attachment = {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};

// Shape returned to a USER-role caller - deliberately has no AI-analysis
// fields at all (not just null-valued ones), mirroring FeedbackUserRead
// on the backend. Components for this shape must only ever destructure
// these fields, never spread the object, so a stray backend field can't
// leak into the DOM.
export type FeedbackUser = {
  id: number;
  raw_text: string;
  status: FeedbackStatus;
  acknowledgement: string | null;
  admin_response: string | null;
  admin_response_at: string | null;
  attachments: Attachment[];
  source: FeedbackSource | null;
  product: string | null;
  module: string | null;
  created_at: string;
  updated_at: string;
};

// Shape returned to an ADMIN-role caller - everything a user sees, plus
// AI analysis results and admin-only workflow fields.
export type FeedbackAdmin = FeedbackUser & {
  main_category: MainCategory | null;
  sub_category: string | null;
  sentiment: Sentiment | null;
  priority: Priority | null;
  confidence: number | null;
  summary: string | null;
  themes: string[];
  tags: string[];
  internal_notes: string | null;
  user_id: number | null;
  submitter_user_id_legacy: string | null;
  name: string | null;
  email: string | null;
  version: string | null;
  device: string | null;
  browser: string | null;
  platform: string | null;
  region: string | null;
};

export type FeedbackCreatePayload = {
  raw_text: string;
  source?: FeedbackSource;
  device?: string;
  browser?: string;
  platform?: string;
};

export type FeedbackAdminUpdatePayload = {
  status?: FeedbackStatus;
  priority?: Priority;
  tags?: string[];
  internal_notes?: string;
  admin_response?: string;
};

export type FeedbackListFilters = {
  skip?: number;
  limit?: number;
  main_category?: MainCategory;
  sentiment?: Sentiment;
  search?: string;
  source?: FeedbackSource;
  product?: string;
};
