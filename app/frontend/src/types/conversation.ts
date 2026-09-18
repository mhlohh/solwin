// Canonical types mirroring app/Backend Pydantic schemas.

export type ChannelType = 'EMAIL' | 'CHAT' | 'TICKET' | 'SOCIAL_MEDIA' | 'OTHER';
export type ConversationStatusType = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
export type SenderType = 'CUSTOMER' | 'AGENT' | 'SYSTEM';
export type PriorityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type SentimentType = 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ResolutionStatusType = 'RESOLVED' | 'UNRESOLVED' | 'PARTIALLY_RESOLVED' | 'UNKNOWN';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'SUPPORT_AGENT' | 'SUPPORT_MANAGER' | 'SECURITY_ANALYST' | 'ADMIN';
  is_active: boolean;
  created_at: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: SenderType;
  sender_name?: string | null;
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  conversation_reference: string;
  customer_name?: string | null;
  customer_email?: string | null;
  channel: ChannelType;
  subject?: string | null;
  status: ConversationStatusType;
  assigned_agent_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRecord {
  id: string;
  conversation_id: string;
  category?: string | null;
  issue?: string | null;
  sentiment?: string | null;
  emotion?: string | null;
  priority?: string | null;
  resolution_status?: string | null;
  summary?: string | null;
  recommended_action?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  assigned_agent?: User | null;
  messages: Message[];
  analysis_records: AnalysisRecord[];
  threat_records: Threat[];
}

export interface ConversationCreate {
  customer_name?: string;
  customer_email?: string;
  channel?: ChannelType;
  subject?: string;
  initial_message?: string;
}

export interface ConversationFilterParams {
  page?: number;
  page_size?: number;
  status?: ConversationStatusType | '';
  channel?: ChannelType | '';
  assigned_agent_id?: string;
  search?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

// ---- Unified intelligence payloads (POST /analyze) ----

export interface CustomerIntelligence {
  category: string;
  issue: string;
  sentiment: SentimentType;
  emotion: string;
  priority: PriorityLevel;
  resolution_status: ResolutionStatusType;
  summary: string;
}

export interface SecurityIntelligence {
  threat_detected: boolean;
  threat_type: string;
  suspicious_urls: string[];
  suspicious_emails: string[];
  social_engineering_detected: boolean;
  techniques: string[];
  risk_level: string;
  risk_reasons: string[];
}

export interface UnifiedAnalysis {
  conversation_id: string | null;
  customer_intelligence: CustomerIntelligence;
  security_intelligence: SecurityIntelligence;
  recommended_action: string;
}

// ---- Threat records (GET /security/threats) ----

export interface Threat {
  id: string;
  conversation_id?: string | null;
  threat_detected: boolean;
  threat_type?: string | null;
  social_engineering_detected: boolean;
  techniques: string[];
  risk_level?: string | null;
  suspicious_urls: string[];
  suspicious_emails: string[];
  risk_reasons: string[];
  recommended_action?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ThreatFilterParams {
  page?: number;
  page_size?: number;
  risk_level?: string | '';
  threat_detected?: boolean;
  search?: string;
}

// ---- Analytics (GET /dashboard/overview, /analytics/*) ----

export interface IngestedFeedbackStats {
  total_records: number;
  phishing_flagged: number;
  priority_counts: Record<string, number>;
  top_intents: IssueFrequency[];
}

export interface DashboardOverview {
  total_conversations: number;
  open_conversations: number;
  in_progress_conversations: number;
  resolved_conversations: number;
  unresolved_conversations: number;
  urgent_conversations: number;
  threats_detected: number;
  critical_threats: number;
  sentiment_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  ingested_feedback?: IngestedFeedbackStats | null;
}

export interface IssueFrequency {
  issue: string;
  count: number;
}

export interface CustomerAnalytics {
  total_conversations: number;
  category_distribution: Record<string, number>;
  sentiment_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  resolution_status_distribution: Record<string, number>;
  most_frequently_reported_issues: IssueFrequency[];
  unresolved_complaint_count: number;
  urgent_complaint_count: number;
}

export interface RecentThreat {
  threat_id: string;
  conversation_id?: string | null;
  threat_type?: string | null;
  risk_level?: string | null;
  risk_reasons: string[];
  created_at: string;
}

export interface SecurityAnalytics {
  total_threats: number;
  threats_detected: number;
  risk_distribution: Record<string, number>;
  threat_type_distribution: Record<string, number>;
  technique_frequency: Record<string, number>;
  suspicious_url_count: number;
  suspicious_email_count: number;
  recent_critical_threats: RecentThreat[];
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface TrendResponse {
  days: number;
  total_count: number;
  trends: TrendPoint[];
}
