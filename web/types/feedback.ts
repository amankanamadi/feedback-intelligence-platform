export type FeedbackStatus = "New" | "Acknowledged" | "In Review" | "In Progress" | "Resolved" | "Closed";
export type Priority = "Low" | "Medium" | "High" | "Critical";
export type Sentiment = "Positive" | "Neutral" | "Negative";
export type MainCategory = "Guest Review" | "Host Complaint" | "Support Ticket";
export type SubCategory =
  | "Cleanliness"
  | "WiFi"
  | "Check-in"
  | "Amenities"
  | "Host Communication"
  | "Safety"
  | "Maintenance"
  | "Booking Experience"
  | "Payments"
  | "Refunds"
  | "App Issues"
  | "Feature Requests";
export type FeedbackSource =
  | "Mobile App"
  | "Website"
  | "Post-Stay Survey"
  | "Host Dashboard"
  | "Email"
  | "Support Chat"
  | "API"
  | "QR Code";
export type PropertyType = "Entire Home" | "Private Room" | "Shared Room";

export const STATUS_OPTIONS: FeedbackStatus[] = ["New", "Acknowledged", "In Review", "In Progress", "Resolved", "Closed"];
export const PRIORITY_OPTIONS: Priority[] = ["Low", "Medium", "High", "Critical"];
export const MAIN_CATEGORY_OPTIONS: MainCategory[] = ["Guest Review", "Host Complaint", "Support Ticket"];
export const SENTIMENT_OPTIONS: Sentiment[] = ["Positive", "Neutral", "Negative"];

export type Attachment = {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};

export type Property = {
  id: number;
  name: string;
  host_name: string;
  city: string;
  country: string;
  property_type: PropertyType;
};

// Shape returned to a GUEST/HOST-role caller - deliberately has no
// AI-analysis fields at all (not just null-valued ones), mirroring
// FeedbackSubmitterRead on the backend. Components for this shape must
// only ever destructure these fields, never spread the object, so a stray
// backend field can't leak into the DOM.
export type FeedbackUser = {
  id: number;
  raw_text: string;
  status: FeedbackStatus;
  acknowledgement: string | null;
  admin_response: string | null;
  admin_response_at: string | null;
  attachments: Attachment[];
  source: FeedbackSource | null;
  property_id: number | null;
  property_name: string | null;
  property_city: string | null;
  created_at: string;
  updated_at: string;
};

// Shape returned to a STAFF-role caller (Support Manager, Ops Manager,
// Product Manager, Exec) - everything a submitter sees, plus AI analysis
// results and staff-only workflow fields.
export type FeedbackAdmin = FeedbackUser & {
  main_category: MainCategory | null;
  sub_category: string | null;
  sentiment: Sentiment | null;
  priority: Priority | null;
  confidence: number | null;
  summary: string | null;
  recommended_action: string | null;
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
};

export type FeedbackCreatePayload = {
  raw_text: string;
  source?: FeedbackSource;
  property_id?: number;
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
  property_id?: number;
};
