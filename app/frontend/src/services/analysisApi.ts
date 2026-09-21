import { api, getApiErrorMessage } from './api';
import {
  CustomerIntelligence,
  SecurityIntelligence,
  UnifiedAnalysis,
} from '../types/conversation';

/** Trigger full unified intelligence analysis for a conversation (persists results). */
export async function analyzeConversation(
  conversationId: string
): Promise<UnifiedAnalysis> {
  try {
    const response = await api.post<UnifiedAnalysis>('/analyze', {
      conversation_id: conversationId,
    });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Unified analysis failed.'));
  }
}

/** Fetch latest persisted unified analysis without re-invoking AI. */
export async function getUnifiedAnalysis(
  conversationId: string
): Promise<UnifiedAnalysis> {
  try {
    const response = await api.get<UnifiedAnalysis>(
      `/analyze/conversation/${conversationId}`
    );
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load unified analysis.'));
  }
}

/** Direct security analysis on a raw message without persistence. */
export async function analyzeSecurityDirect(
  message: string,
  expectedDomain?: string,
  displayName?: string
): Promise<SecurityIntelligence> {
  try {
    const response = await api.post<SecurityIntelligence>('/security/analyze', {
      message,
      expected_domain: expectedDomain,
      display_name: displayName,
    });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Security analysis failed.'));
  }
}

/** Derive customer intelligence shape from the latest persisted analysis record. */
export function toCustomerIntelligence(
  record: import('../types/conversation').AnalysisRecord | null | undefined
): CustomerIntelligence | null {
  if (!record) return null;
  return {
    category: record.category || 'OTHER',
    issue: record.issue || 'No issue recorded',
    sentiment: (record.sentiment as CustomerIntelligence['sentiment']) || 'NEUTRAL',
    emotion: record.emotion || 'Neutral',
    priority: (record.priority as CustomerIntelligence['priority']) || 'LOW',
    resolution_status:
      (record.resolution_status as CustomerIntelligence['resolution_status']) ||
      'UNKNOWN',
    summary: record.summary || '',
  };
}

export type { CustomerIntelligence };
