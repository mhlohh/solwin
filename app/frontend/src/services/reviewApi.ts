import { api, getApiErrorMessage } from './api';

/** Canonical CustomerReviewOutput — mirrors app/Backend/app/schemas/review.py. */
export interface CustomerReviewIntelligence {
  review_id: string;
  source: { source_type: string; source_record_id: string; domain: string; channel: string };
  content: { subject: string; message: string };
  classification: {
    category: string;
    fine_grained_intent: string;
    confidence: number;
    needs_review: boolean;
  };
  sentiment: { label: string; score: number };
  keywords: string[];
  summary: { text: string };
  clustering: { cluster_id: string; cluster_name: string; similarity_score: number };
  urgency: { level: string; score: number; reasons: string[] };
  resolution: { status: string; confidence: number; evidence: string[] };
  security: {
    risk_level: string;
    risk_score: number;
    phishing: { detected: boolean; confidence: number };
    urls: { url: string; risk_level: string; reasons?: string[] }[];
    email_addresses: { email: string; risk_level: string; reasons?: string[] }[];
    social_engineering: { detected: boolean; techniques: string[] };
    reasons: string[];
  };
  overall_risk: { level: string; score: number; factors: string[] };
  recommendation: {
    primary_action: string;
    priority: string;
    secondary_actions: string[];
    rationale: string;
  };
  model_metadata: Record<string, string>;
  processing: { processed_at: string; processing_time_ms: number; warnings: string[] };
}

/** Canonical review id for a raw dataset record — keeps re-analysis idempotent. */
export function inboxReviewId(ticketId: number): string {
  return `INBOX-${ticketId}`;
}

export async function getStoredReview(
  reviewId: string
): Promise<CustomerReviewIntelligence | null> {
  try {
    const { data } = await api.get<CustomerReviewIntelligence>(`/reviews/${reviewId}`);
    return data;
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 404) return null;
    throw err;
  }
}

export async function analyzeInboxTicket(payload: {
  ticketId: number;
  message: string;
  subject: string;
  domain: string;
  channel: string;
}): Promise<CustomerReviewIntelligence> {
  const { data } = await api.post<CustomerReviewIntelligence>('/reviews', {
    review_id: inboxReviewId(payload.ticketId),
    source_type: 'DATASET',
    source_record_id: String(payload.ticketId),
    domain: payload.domain,
    channel: payload.channel,
    subject: payload.subject,
    message: payload.message,
  });
  return data;
}

export { getApiErrorMessage };
